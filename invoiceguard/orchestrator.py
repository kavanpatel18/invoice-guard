"""Orchestration controller: owns shared state, runs the workflow, bounded correction loop, escalation."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime

from . import tools as T
from .agents import CriticAgent, ExecutorAgent, PlannerAgent, ResearchAgent, ResolutionAgent

FAULT_TRANSIENT = {"type": "inflate_payable", "attempts": [1]}   # wrong on 1st attempt, healthy on retry
FAULT_PERSISTENT = {"type": "force_approve", "attempts": [1, 2]}  # wrong every time -> must escalate
REVIEW_ACTIONS = ["Accept recommendation", "Reject recommendation", "Request more information", "Escalate to finance manager"]
SIMULATED = {"Accept recommendation": "SIMULATED: recommendation executed in ERP sandbox",
             "Reject recommendation": "SIMULATED: recommendation rejected, case returned to AP clerk",
             "Request more information": "SIMULATED: email requesting information sent to vendor",
             "Escalate to finance manager": "SIMULATED: ticket created for finance manager"}


@dataclass
class CaseState:
    invoice: dict
    fault: dict | None = None
    plan: list = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    results: dict = field(default_factory=dict)
    decision: dict = field(default_factory=dict)
    critic_history: list = field(default_factory=list)
    tool_calls: list = field(default_factory=list)
    audit: list = field(default_factory=list)
    attempts: int = 0
    fault_effective: bool = False
    status: str = "NEW"
    needs_human: bool = True
    human_review: dict | None = None
    elapsed_ms: float = 0.0

    def log(self, agent: str, action: str, detail: str = "") -> None:
        self.audit.append({"seq": len(self.audit) + 1, "time": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                           "agent": agent, "action": action, "detail": detail})


def _inject(decision: dict, fault: dict | None, attempt: int, inv: dict) -> tuple[dict, bool]:
    """Fault injection for the demo/tests: corrupts the Resolution output on chosen attempts."""
    if not fault or attempt not in fault["attempts"]:
        return decision, False
    d = dict(decision)
    if fault["type"] == "force_approve":
        d["decision"], d["payable"] = "APPROVE", str(T.invoice_total(inv)) if T.validate_input(inv)["valid"] else "1000.00"
    elif fault["type"] == "inflate_payable":
        base = T.D(d["payable"])
        d["payable"] = str(T.money(base * T.D("1.25") if base else T.D("1000")))
    return d, d != decision


def process_invoice(invoice: dict, dataset: dict, policy: dict | None = None, fault: dict | None = None,
                    max_attempts: int = 2) -> CaseState:
    policy = policy or T.load_policy()
    if invoice.get("vendor_id") and invoice["vendor_id"] not in dataset["vendors"]:
        raise ValueError(f"Unknown vendor_id {invoice['vendor_id']!r}: vendor master has no such record")
    t0 = time.perf_counter()
    s = CaseState(invoice=invoice, fault=fault)
    planner, research, executor, resolver, critic = PlannerAgent(), ResearchAgent(), ExecutorAgent(), ResolutionAgent(), CriticAgent()
    s.log("Orchestrator", "case opened", f"{invoice.get('invoice_id', '(custom)')} / vendor {invoice.get('vendor_id')}")

    s.plan = planner.plan(invoice, dataset, policy["params"])
    s.log("Planner", "plan created", " -> ".join(t["task"] for t in s.plan))
    s.evidence = research.gather(invoice, dataset)
    s.log("Research", "records retrieved", f"vendor={'yes' if s.evidence['vendor'] else 'no'}, PO={'yes' if s.evidence['po'] else 'no'}, "
          f"GRN={'yes' if s.evidence['grn'] else 'no'}, history={len(s.evidence['history'])}")

    passed = False
    for attempt in range(1, max_attempts + 1):
        s.attempts = attempt
        for t in s.plan:
            if t["owner"] == "Executor":
                t["status"] = "pending"
        s.results = executor.run(s, policy)
        s.log("Executor", f"tools executed (attempt {attempt})", f"findings={s.results['findings'] or 'none'}")
        decision = resolver.decide(s, policy)
        decision["clauses"] = research.cite(decision["reasons"], policy)
        s.log("Resolution", "decision proposed", f"{decision['decision']} payable={decision['payable']}")
        decision, changed = _inject(decision, fault, attempt, invoice)
        if changed:
            s.fault_effective = True
            s.log("FAULT-INJECTION", "Resolution output corrupted", f"{fault['type']} -> {decision['decision']} payable={decision['payable']}")
        s.decision = decision
        report = critic.review(s, policy, dataset)
        s.critic_history.append(report)
        failed = [c["id"] for c in report["checks"] if not c["passed"]]
        s.log("Critic", "validation " + ("PASSED" if report["passed"] else "FAILED"), f"failed checks: {failed}" if failed else "all 8 checks passed")
        if report["passed"]:
            passed = True
            break
        if attempt < max_attempts:
            s.log("Orchestrator", "correction loop", f"re-running Executor + Resolution (attempt {attempt + 1}/{max_attempts})")

    if not passed:
        s.decision = {"decision": "ESCALATE", "reasons": ["CRITIC_UNRESOLVED"], "payable": "0.00",
                      "not_paid": s.results.get("invoice_total", "0.00"), "clauses": {}}
        s.status, s.needs_human = "ESCALATED_CRITIC_FAILURE", True
        s.log("Orchestrator", "escalated", "Critic still failing after bounded retries; payment blocked, sent to human")
    elif s.decision["decision"] == "APPROVE":
        s.status, s.needs_human = "AUTO_APPROVED_SIMULATED", False
        s.log("Orchestrator", "auto-approved (simulated)", "clean match, below approval limit, Critic passed")
    else:
        s.status, s.needs_human = "PENDING_HUMAN_REVIEW", True
        s.log("Orchestrator", "routed to human review", f"recommendation={s.decision['decision']}")
    s.elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return s


def apply_human_review(state: CaseState, action: str, note: str = "") -> CaseState:
    if action not in REVIEW_ACTIONS:
        raise ValueError(f"unknown review action {action!r}")
    state.human_review = {"action": action, "note": note, "simulated_effect": SIMULATED[action],
                          "time": datetime.now().isoformat(timespec="seconds")}
    state.status = "REVIEWED_" + action.upper().replace(" ", "_")
    state.log("Human reviewer", action, note or SIMULATED[action])
    return state

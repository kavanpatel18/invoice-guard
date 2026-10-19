"""Batch evaluation against generator ground truth, baseline comparison and fault experiments."""
from __future__ import annotations

import pandas as pd

from .baseline import baseline_decision
from .orchestrator import FAULT_PERSISTENT, FAULT_TRANSIENT, process_invoice
from .tools import load_policy


def run_batch(ds: dict, policy: dict | None = None, fault: dict | None = None) -> list:
    policy = policy or load_policy()
    return [process_invoice(inv, ds, policy, fault) for inv in ds["invoices"]]


def results_table(ds: dict, states: list) -> pd.DataFrame:
    rows = []
    for s in states:
        iid = s.invoice["invoice_id"]
        gt = ds["ground_truth"][iid]
        rows.append({"invoice_id": iid, "vendor": ds["vendors"][s.invoice["vendor_id"]]["name"],
                     "scenario": gt["label"], "anomaly": gt["anomaly"], "expected": gt["expected_decision"],
                     "decision": s.decision["decision"], "correct": s.decision["decision"] == gt["expected_decision"],
                     "expected_payable": gt["expected_payable"], "payable": float(s.decision["payable"]),
                     "payable_ok": abs(float(s.decision["payable"]) - gt["expected_payable"]) <= 0.01,
                     "reasons": ", ".join(s.decision["reasons"]), "attempts": s.attempts,
                     "critic_first_pass": s.critic_history[0]["passed"], "needs_human": s.needs_human,
                     "status": s.status, "ms": s.elapsed_ms})
    return pd.DataFrame(rows)


def summary(df: pd.DataFrame) -> dict:
    n = len(df)
    return {"cases": n, "decision_accuracy": float(round(df.correct.mean() * 100, 1)), "payable_accuracy": float(round(df.payable_ok.mean() * 100, 1)),
            "critic_first_pass_pct": float(round(df.critic_first_pass.mean() * 100, 1)), "auto_approved": int((~df.needs_human).sum()),
            "human_review": int(df.needs_human.sum()), "avg_ms": float(round(df.ms.mean(), 2)),
            "wrong_auto_approvals": int(((df.decision == "APPROVE") & (df.expected != "APPROVE")).sum())}


def baseline_table(ds: dict) -> pd.DataFrame:
    rows = []
    for inv in ds["invoices"]:
        gt = ds["ground_truth"][inv["invoice_id"]]
        rows.append({"invoice_id": inv["invoice_id"], "anomaly": gt["anomaly"], "expected": gt["expected_decision"],
                     "baseline": baseline_decision(inv, ds)})
    return pd.DataFrame(rows)


def compare(ds: dict, df: pd.DataFrame) -> pd.DataFrame:
    b = baseline_table(ds)
    bad_b = int(((b.baseline == "APPROVE") & (b.expected != "APPROVE")).sum())
    ok_b = int(((b.baseline == "APPROVE") & (b.expected == "APPROVE")).sum())
    exp_ok = int((b.expected == "APPROVE").sum())
    a = summary(df)
    out = pd.DataFrame([
        {"metric": "Invoices", "baseline 2-way match": len(b), "InvoiceGuard agents": a["cases"]},
        {"metric": "Auto-approved (no human)", "baseline 2-way match": int((b.baseline == "APPROVE").sum()), "InvoiceGuard agents": a["auto_approved"]},
        {"metric": "Auto-approved WRONGLY (should not be paid in full)", "baseline 2-way match": bad_b, "InvoiceGuard agents": a["wrong_auto_approvals"]},
        {"metric": "Legitimate invoices auto-approved", "baseline 2-way match": f"{ok_b}/{exp_ok}", "InvoiceGuard agents": f"{int(((df.decision=='APPROVE')&(df.expected=='APPROVE')).sum())}/{exp_ok}"},
        {"metric": "Cases routed to a human with NO diagnosis", "baseline 2-way match": int((b.baseline == "MANUAL").sum()), "InvoiceGuard agents": 0},
        {"metric": "Cases routed to a human WITH diagnosis + cited policy", "baseline 2-way match": 0, "InvoiceGuard agents": a["human_review"]},
        {"metric": "Decision accuracy vs ground truth", "baseline 2-way match": "n/a (cannot decide exceptions)", "InvoiceGuard agents": f"{a['decision_accuracy']}%"},
    ])
    return out.astype(str)


def fault_experiment(ds: dict, kind: str) -> pd.DataFrame:
    fault = FAULT_TRANSIENT if kind == "transient" else FAULT_PERSISTENT
    rows = []
    for inv in ds["invoices"]:
        s = process_invoice(inv, ds, fault=fault)
        gt = ds["ground_truth"][inv["invoice_id"]]
        rows.append({"invoice_id": inv["invoice_id"], "fault_effective": s.fault_effective,
                     "detected_first_attempt": (not s.critic_history[0]["passed"]) if s.fault_effective else None,
                     "final_decision": s.decision["decision"], "attempts": s.attempts, "status": s.status,
                     "final_correct": s.decision["decision"] == gt["expected_decision"] and
                     abs(float(s.decision["payable"]) - gt["expected_payable"]) <= 0.01,
                     "safe_outcome": float(s.decision["payable"]) <= gt["expected_payable"] + 0.01,
                     "unsafe_payment_released": s.decision["decision"] in ("APPROVE", "PAY_PARTIAL") and
                     float(s.decision["payable"]) > gt["expected_payable"] + 0.01})
    return pd.DataFrame(rows)

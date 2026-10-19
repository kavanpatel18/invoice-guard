import copy
import pytest
from conftest import first
from invoiceguard.agents import CriticAgent, PlannerAgent, ResearchAgent, FINDING_QUERY
from invoiceguard.orchestrator import process_invoice


def names(plan):
    return [t["task"] for t in plan]


def test_planner_state_dependent(ds, policy):
    p = PlannerAgent()
    clean = names(p.plan(first(ds, "CLEAN"), ds, policy["params"]))
    assert clean[:5] == ["validate_input", "duplicate_check", "bank_check", "tax_check", "three_way_match"]
    assert "flag_missing_po" in names(p.plan(first(ds, "NO_PO"), ds, policy["params"]))
    bad = copy.deepcopy(first(ds, "CLEAN")); bad["invoice_no"] = ""
    short = names(p.plan(bad, ds, policy["params"]))
    assert short == ["validate_input", "apply_policy_decision", "independent_validation", "route_for_review"]


def test_plan_dependencies_reference_existing_tasks(ds, policy):
    plan = PlannerAgent().plan(first(ds, "CLEAN"), ds, policy["params"])
    ids = {t["id"] for t in plan}
    assert all(d in ids for t in plan for d in t["depends_on"])


EXPECTED_CLAUSE = {"INPUT_INVALID": "AP-0", "BANK_MISMATCH": "AP-6", "DUPLICATE_INVOICE": "AP-5", "NO_PO": "AP-1",
                   "SKU_NOT_ON_PO": "AP-1", "NO_GRN": "AP-4", "TAX_RATE_MISMATCH": "AP-7",
                   "PRICE_OVER_TOLERANCE": "AP-2", "QTY_OVER_RECEIVED": "AP-3", "OVER_APPROVAL_LIMIT": "AP-8"}


@pytest.mark.parametrize("code,clause", EXPECTED_CLAUSE.items())
def test_retrieval_returns_right_clause(policy, code, clause):
    assert ResearchAgent().cite([code], policy)[code]["clause_id"] == clause


def test_research_gathers_only_vendor_history(ds):
    inv = first(ds, "CLEAN"); ev = ResearchAgent().gather(inv, ds)
    assert ev["po"]["po_id"] == inv["po_id"] and all(h["vendor_id"] == inv["vendor_id"] for h in ev["history"])


def test_critic_passes_on_healthy_case(ds, policy):
    s = process_invoice(first(ds, "QTY_OVER"), ds, policy)
    rep = CriticAgent().review(s, policy, ds)
    assert rep["passed"] and len(rep["checks"]) == 8


def test_critic_detects_wrong_decision_and_amount(ds, policy):
    s = process_invoice(first(ds, "DUPLICATE"), ds, policy)
    s.decision = {**s.decision, "decision": "APPROVE", "payable": s.results["invoice_total"]}
    rep = CriticAgent().review(s, policy, ds)
    failed = {c["id"] for c in rep["checks"] if not c["passed"]}
    assert not rep["passed"] and {"K3", "K4", "K6"} <= failed


def test_critic_detects_tampered_findings_and_skipped_control(ds, policy):
    s = process_invoice(first(ds, "BANK_CHANGE"), ds, policy)
    s.results = {**s.results, "findings": []}
    assert "K2" in {c["id"] for c in CriticAgent().review(s, policy, ds)["checks"] if not c["passed"]}
    s2 = process_invoice(first(ds, "CLEAN"), ds, policy)
    s2.plan = [t for t in s2.plan if t["task"] != "bank_check"]
    assert "K8" in {c["id"] for c in CriticAgent().review(s2, policy, ds)["checks"] if not c["passed"]}


def test_critic_detects_uncited_reason(ds, policy):
    s = process_invoice(first(ds, "NO_GRN"), ds, policy)
    s.decision = {**s.decision, "clauses": {}}
    assert "K7" in {c["id"] for c in CriticAgent().review(s, policy, ds)["checks"] if not c["passed"]}

import copy
import pytest
from conftest import first
from invoiceguard.data_gen import EXPECTED, PLAN, generate_dataset
from invoiceguard.evaluation import compare, fault_experiment, results_table, run_batch, summary
from invoiceguard.orchestrator import (FAULT_PERSISTENT, FAULT_TRANSIENT, REVIEW_ACTIONS, apply_human_review,
                                       process_invoice)


@pytest.mark.parametrize("anomaly", list(EXPECTED))
def test_each_scenario_matches_ground_truth(ds, policy, anomaly):
    inv = first(ds, anomaly); s = process_invoice(inv, ds, policy); gt = ds["ground_truth"][inv["invoice_id"]]
    assert s.decision["decision"] == gt["expected_decision"]
    assert float(s.decision["payable"]) == pytest.approx(gt["expected_payable"], abs=0.01)
    assert s.critic_history[-1]["passed"]


def test_full_batch_metrics(ds, policy):
    df = results_table(ds, run_batch(ds, policy)); m = summary(df)
    assert m["cases"] == sum(PLAN.values()) == 63
    assert m["decision_accuracy"] == 100.0 and m["wrong_auto_approvals"] == 0


def test_reproducible_dataset():
    assert generate_dataset(7) == generate_dataset(7) and generate_dataset(7) != generate_dataset(8)


def test_priority_bank_change_beats_qty_over(ds, policy):
    s = process_invoice(first(ds, "MULTI_BANK_QTY"), ds, policy)
    assert s.decision["decision"] == "ESCALATE" and {"BANK_MISMATCH", "QTY_OVER_RECEIVED"} <= set(s.decision["reasons"])


def test_high_value_clean_invoice_escalates(ds, policy):
    s = process_invoice(first(ds, "HIGH_VALUE"), ds, policy)
    assert "OVER_APPROVAL_LIMIT" in s.decision["reasons"] and s.needs_human


def test_auto_approve_only_when_clean(ds, policy):
    assert process_invoice(first(ds, "CLEAN"), ds, policy).status == "AUTO_APPROVED_SIMULATED"
    assert process_invoice(first(ds, "PRICE_OVER"), ds, policy).status == "PENDING_HUMAN_REVIEW"


def test_missing_and_invalid_inputs_hold(ds, policy):
    bad = copy.deepcopy(first(ds, "CLEAN")); bad["invoice_no"] = ""; bad["lines"][0]["qty"] = 0
    s = process_invoice(bad, ds, policy)
    assert s.decision["decision"] == "HOLD" and s.decision["reasons"] == ["INPUT_INVALID"] and s.decision["clauses"]["INPUT_INVALID"]["clause_id"] == "AP-0"
    assert [t["task"] for t in s.plan if t["owner"] == "Executor"] == ["validate_input"]


def test_unknown_vendor_raises_clear_error(ds, policy):
    bad = copy.deepcopy(first(ds, "CLEAN")); bad["vendor_id"] = "V999"
    with pytest.raises(ValueError, match="Unknown vendor"):
        process_invoice(bad, ds, policy)


def test_unknown_po_reference_is_no_po(ds, policy):
    inv = copy.deepcopy(first(ds, "CLEAN")); inv["po_id"] = "PO-DOES-NOT-EXIST"
    assert process_invoice(inv, ds, policy).decision["reasons"] == ["NO_PO"]


def test_transient_fault_detected_and_corrected(ds, policy):
    s = process_invoice(first(ds, "QTY_OVER"), ds, policy, FAULT_TRANSIENT)
    assert s.fault_effective and s.attempts == 2 and not s.critic_history[0]["passed"] and s.critic_history[1]["passed"]
    assert s.decision["decision"] == "PAY_PARTIAL" and s.status == "PENDING_HUMAN_REVIEW"


def test_persistent_fault_escalates_and_blocks_payment(ds, policy):
    s = process_invoice(first(ds, "DUPLICATE"), ds, policy, FAULT_PERSISTENT)
    assert s.attempts == 2 and s.status == "ESCALATED_CRITIC_FAILURE" and s.decision["payable"] == "0.00" and s.needs_human


def test_fault_experiments_over_whole_dataset(ds):
    t = fault_experiment(ds, "transient"); e = t[t.fault_effective]
    assert len(e) == 63 and e.detected_first_attempt.all() and e.final_correct.all()
    p = fault_experiment(ds, "persistent"); e = p[p.fault_effective]
    assert len(e) > 0 and e.detected_first_attempt.all() and e.safe_outcome.all() and not e.unsafe_payment_released.any()


def test_human_review_actions_and_validation(ds, policy):
    s = process_invoice(first(ds, "NO_GRN"), ds, policy)
    for a in REVIEW_ACTIONS:
        apply_human_review(s, a, "note")
        assert s.human_review["action"] == a and s.human_review["simulated_effect"].startswith("SIMULATED")
    with pytest.raises(ValueError):
        apply_human_review(s, "Pay immediately")


def test_audit_log_has_all_agents(ds, policy):
    agents = {a["agent"] for a in process_invoice(first(ds, "CLEAN"), ds, policy).audit}
    assert {"Orchestrator", "Planner", "Research", "Executor", "Resolution", "Critic"} <= agents


def test_comparison_and_exports(ds, policy):
    df = results_table(ds, run_batch(ds, policy)); cmp = compare(ds, df)
    assert "baseline 2-way match" in cmp.columns
    csv = df.to_csv(index=False); assert csv.startswith("invoice_id") and len(csv.splitlines()) == 64

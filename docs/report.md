# Deliverable D — Project Report: InvoiceGuard

## 1. Problem and domain
See `problem_statement.md`. Domain: Accounts Payable exception handling. Chosen over 8 other candidates by a weighted model (`candidate_selection.md`, my judgement: 90/100 vs next best 79).

## 2. Existing vs proposed workflow
Existing: clerk manually gathers PO/GRN/vendor/history and policy, decides, emails vendor; baseline automation = total-only 2-way match.
Proposed: Planner → Research → Executor(tools) → Resolution → Critic (loop ≤2) → auto-approve or human review. Failure at any stage ends in a blocked payment and human escalation.

## 3. Architecture and agent responsibilities
| Agent | Responsibility | Inputs → Outputs | Failure condition |
|---|---|---|---|
| Planner | Plan depends on invoice: invalid → short plan; PO present → 3-way match else flag missing PO | invoice → ordered tasks with dependencies | — |
| Research | Fetch vendor/PO/GRN/history; retrieve policy clause per finding | invoice → evidence; finding → clause id | missing records returned as None |
| Executor | Runs tools: validate, duplicate, bank, GST, 3-way match, payable | plan+evidence → findings, amounts | logs each call |
| Resolution | Priority rules: findings → decision | findings → decision, payable, reasons | — |
| Critic | Re-derives findings/decision/amount from RAW dataset using exact fractions; 8 checks (K1–K8) | state → pass/fail per check | any fail ⇒ retry/escalate |
| Orchestrator | Shared `CaseState`, correction loop (max 2), escalation, routing, audit log | invoice → final state | persistent failure ⇒ ESCALATE, payable 0 |

Genuine-agentic evidence: state-dependent plan, tool calls with logged results, retrieval, decision logic, independent validation, bounded correction, escalation, human approval.

## 4. Business logic and formulas
* Invoice total = Σ(qty × unit_price) × (1 + tax_rate), rounded half-up to 0.01 (Decimal in tools; exact fractions in the Critic).
* Price variance % = (invoice price − PO price) / PO price × 100; violation if > 2.0.
* Quantity violation if invoice qty > received qty (tolerance 0).
* Partial payable = Σ min(invoice qty, received qty) × invoice price × (1 + tax).
* GST: registered vendors 18%, unregistered 0%.
* Duplicate: same vendor and normalised invoice number within 90 days (or same amount + date).
* Limit: payable > INR 5,00,000 ⇒ ESCALATE.

## 5. Dataset
`data_gen.py`, seed 42: 8 vendors, 63 invoices, 59 POs, 55 GRNs, 21 history records. 13 scenarios (clean ×18, price in tolerance ×5, price over ×5, over-billing ×6, no GRN ×4, duplicate ×5, bank change ×4, wrong GST ×4, no PO ×4, high value ×3, arithmetic error ×2, bank+over-billing ×2, duplicate+price ×1). Ground-truth labels are written by the generator, not by the agents. All synthetic.

## 6. Validation and testing (executed)
* `python -m pytest tests -v`: **56 passed** (tools, schemas/inputs, planner, retrieval, critic, workflow, faults, human review, exports, Streamlit AppTest). Log: `pytest_results.txt`.
* Test matrix: **19/19 passed** (`test_matrix.md`), incl. invalid inputs, unknown PO, transient and persistent faults.
* Unknown vendor id raises a clear `ValueError` (shown as an error in the UI).

## 7. Actual results (synthetic seed 42, measured)
| Measure | Result |
|---|---|
| Decision accuracy vs generator labels | 63/63 (100%) |
| Payable-amount accuracy | 63/63 (100%) |
| Critic first-pass rate (no faults) | 100% |
| Auto-approved / sent to human | 23 / 40 |
| Wrongly auto-approved (agents) | 0 |
| Baseline 2-way match: auto-approved / wrongly approved | 53 / 30 |
| Baseline: routed to human without diagnosis | 10 |
| Avg processing time | 0.24 ms per case (pure Python, no LLM) |
| Fault injection (transient, wrong payable on attempt 1) | 63/63 detected on first attempt, 63/63 corrected on retry |
| Fault injection (persistent wrong approval) | 40 effective, 40/40 detected, all escalated, 0 unsafe payments released |
(In the persistent run 23 clean invoices were unaffected because "approve" was already correct, so the injected fault changed nothing; we count only effective faults.)

**Caveat:** 100% accuracy is against labels produced by the same author's generator and rules. It shows the implementation is consistent and the Critic's independent re-derivation agrees; it is *not* evidence of real-world accuracy. No time or money savings are claimed.

## 8. Limitations
Synthetic data and simplified rules; no OCR/ERP/bank integration; duplicate and GST logic simplified; LLM (optional) only rephrases text; Critic shares the policy parameters with the Executor; in-session human-review log only; single-currency.

## 9. Future scope (not implemented)
Invoice OCR/PDF ingestion; LangGraph graph orchestration; ERP connector via MCP; learning thresholds from clerk overrides; vendor risk scoring; multi-invoice/partial-delivery matching; authentication and role-based approval.

# Deliverable A — Problem Statement

**Title:** InvoiceGuard — an agentic workflow for resolving supplier-invoice exceptions in Accounts Payable
**Domain:** Finance operations / Accounts Payable (business operations and document management)

## 1. Business background
Companies pay suppliers only after matching the **invoice** to the **purchase order (PO)** and the **goods receipt note (GRN)** ("3-way match"). Invoices that do not match are *exceptions*. Accounts-payable clerks must work out why, apply company policy, decide whether to pay, short-pay, hold, reject or escalate, and contact the vendor.

## 2. Users and stakeholders
AP clerks (primary user), finance manager (approver), procurement/warehouse (PO/GRN owners), vendors, internal audit.

## 3. Existing process
1. Invoice arrives; clerk keys/checks fields.
2. System/clerk compares invoice to PO (often only totals — a "2-way" check).
3. Mismatches go to a shared queue; the clerk manually opens PO, GRN, vendor master and past invoices, reads the policy, decides, and emails the vendor.
4. A manager signs off high-value or risky items.

## 4. Inefficiencies and risks
* A total-only match misses goods not received, over-billing, duplicates re-submitted with a different number format, wrong GST rate and changed bank details. In our synthetic data a naive 2-way rule wrongly auto-approved **30 of the 53** invoices it approved (measured, see report).
* Exception diagnosis is manual, repetitive and inconsistent between clerks.
* Bank-detail changes are a known fraud vector: FBI IC3's 2024 report lists business email compromise at about USD 2.8 billion in reported losses (source: Nacha summary, 24 Apr 2025).

## 5. Problem to solve
Given an invoice and the company's records, **decide the correct handling of the invoice, justify it with policy, calculate the payable amount, and independently verify the result before any money-related action**, escalating to a human whenever the system is unsure or the case is risky.

## 6. Why an agentic approach
The task needs planning (which checks apply depends on the invoice), retrieval (records + policy), tool execution (exact calculations), a decision, and — critically — an **independent validator** with a bounded correction loop and escalation. A single prompt/chatbot cannot give an independent, auditable check on money-moving decisions.

## 7. Proposed solution
Five agents plus an orchestrator (Planner, Research, Executor, Resolution, Critic) operating on shared case state, exposed in a Streamlit app with human review. See `architecture.md`.

## 8. Objectives (all measured in the PoC)
1. Correctly classify each synthetic invoice into APPROVE / PAY_PARTIAL / HOLD / REJECT / ESCALATE (vs ground-truth labels).
2. Compute the payable amount exactly for approved and short-paid cases.
3. Release **zero** wrongly auto-approved invoices, versus a 2-way-match baseline.
4. Detect injected faulty outputs with the Critic (detection rate) and either correct them or escalate without releasing payment.
5. Make every decision explainable: plan, tool calls, cited policy clauses, critic checks, audit log.

## 9. Scope and boundaries
In scope: one invoice workflow, 13 synthetic anomaly types, 8 vendors, rule-based policy (`policy.json`). Out of scope: OCR of real invoices, real ERP/bank integration, multi-currency, partial deliveries across several invoices, learning from feedback.

## 10. Assumptions and constraints
Synthetic data only; tolerance 2%, approval limit INR 5,00,000, GST 18% are **illustrative assumptions**; no paid APIs; payments/emails are simulated; PoC, not production-ready.

## 11. Expected benefits (qualitative, not claimed as measured savings)
Fewer wrong payments, faster and more consistent diagnosis, auditable reasoning, clerks see a recommendation with evidence instead of a raw exception.

## 12. Success criteria
Decision accuracy and payable accuracy on the synthetic set; wrong auto-approvals = 0; fault detection rate; no payment released under injected persistent fault; all tests pass.

## References
* Nacha, "FBI's IC3 Finds Almost $8.5 Billion Lost to Business Email Compromise in Last Three Years", 24 Apr 2025 — https://www.nacha.org/news/fbis-ic3-finds-almost-85-billion-lost-business-email-compromise-last-three-years (reports IC3 2024: BEC ≈ $2.8B, 21,442 complaints).
* All other figures in this project are synthetic or stated assumptions.

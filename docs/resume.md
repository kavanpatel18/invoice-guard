# Deliverable H — Résumé entry

**InvoiceGuard — Agentic Accounts-Payable Exception Resolution** (Academic project, SIT Pune, 2026)
*Python, Streamlit, pandas, pytest, Decimal/Fractions, Mermaid*
* Designed a 5-agent workflow (Planner, Research, Executor, Resolution, Critic) with a shared-state orchestrator that plans, retrieves policy clauses, executes deterministic tools, and routes invoices to approve / short-pay / hold / reject / escalate.
* Built an independent Critic that re-derives findings, decisions and amounts from raw data (exact fractions) with bounded retry and escalation; fault-injection tests show injected errors detected 63/63 (transient) and 40/40 (persistent) with no payment released under persistent failure.
* Generated a reproducible synthetic dataset (63 invoices, 13 anomaly types) with ground-truth labels; agents matched labels on 63/63 cases versus a 2-way-match baseline that wrongly auto-approved 30; 56 automated tests passing. (Synthetic data; not production-validated.)

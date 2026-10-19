# Deliverable G — Viva Q&A (answers reflect the actual code)

1. **What makes this agentic, not a chatbot?** The Orchestrator runs a state-dependent plan, agents call tools, decide, validate each other and loop/escalate; there is no free-text chat. See `orchestrator.process_invoice`.
2. **Why these agents?** Each has a distinct job: Planner (what to do), Research (evidence + policy), Executor (calculations), Resolution (decision), Critic (independent check). No duplicates.
3. **How does the Planner decide?** It validates the invoice; invalid → short plan; PO exists → `three_way_match`, else `flag_missing_po`. Tested in `test_planner_state_dependent`.
4. **What is shared state?** `CaseState` dataclass: plan, evidence, results, decision, critic history, tool calls, audit log, status.
5. **Where is an LLM used?** Nowhere in decisions. Optional Ollama only rephrases the explanation; numbers are verified and a template is used if they differ or Ollama is down.
6. **Why no LLM for decisions?** Money-affecting rules must be deterministic, testable and auditable; an LLM could invent numbers.
7. **How does the Critic stay independent?** It reads the raw dataset itself, uses its own code and exact `Fraction` arithmetic, and compares findings, decision, payable and plan completeness (8 checks). It shares only policy parameters.
8. **What if Critic and Executor share the same bug?** Possible for shared policy semantics; hence ground-truth labels from the generator and hand-written test-matrix expectations are a third reference. Listed as a limitation.
9. **What happens on failure?** Retry Executor+Resolution once; if still failing, ESCALATE with payable 0 and human review (`ESCALATED_CRITIC_FAILURE`).
10. **What is fault injection?** `_inject` corrupts the Resolution output (inflated payable or forced approve) on chosen attempts. Transient: detected and fixed on retry (63/63). Persistent: 40/40 detected, escalated, nothing released.
11. **Why count only 40 effective persistent faults?** Forcing "approve" on invoices already approved changes nothing, so no fault exists to detect.
12. **How is retrieval done?** IDF-weighted keyword overlap between a finding description and clause title/text/tags (`ResearchAgent.retrieve`); tests assert the right clause for all 10 finding codes. It's simple on purpose; embeddings are future work.
13. **Decision priority?** Input invalid > bank mismatch > duplicate > no PO/unknown SKU > no GRN > GST > price > limit > over-billing > approve. Bank change outranks over-billing (tested).
14. **Why escalate bank changes?** Changed bank details are a fraud pattern (FBI IC3 2024: BEC ≈ $2.8B reported). Policy AP-6 blocks payment pending call-back.
15. **How are amounts calculated?** Decimal with half-up rounding in tools; fractions in the Critic. Partial payable = Σ min(billed, received) × price × (1+tax).
16. **How was the dataset designed?** Seeded generator; 13 scenarios incl. edge cases (reformatted duplicate numbers, tolerance boundary, multi-anomaly). Ground truth is written by the generator.
17. **Why is accuracy 100%, is that suspicious?** Labels and rules both come from me; it shows internal consistency, not real-world accuracy. Real data would produce errors.
18. **Baseline?** Naive 2-way match: invoice subtotal vs PO subtotal within 2%. It auto-approved 53 invoices, 30 wrongly; the agents auto-approved 23, 0 wrongly.
19. **Metrics used?** Decision accuracy, payable accuracy, wrong auto-approvals, critic first-pass, fault detection, unsafe payments released, processing time.
20. **Human oversight?** Only clean invoices below the limit auto-approve (simulated); all others need accept/reject/request-info/escalate; actions logged to a CSV.
21. **Security/privacy?** Synthetic data only; no secrets; no network by default; real deployment would need authN/authZ, audit storage and PII controls (not implemented).
22. **Scalability?** Per-case work is ~0.24 ms in-process; a real system would need a DB, queue, concurrency and integrations — not built.
23. **Why not LangGraph/MCP?** Not needed for 5 sequential agents; a plain controller is easier to test and explain. LangGraph would be a natural next step for branching graphs; MCP for ERP tools.
24. **Biggest limitation?** Synthetic data and simplified rules; no OCR/ERP; single currency.

# Deliverable F — 5-minute demo guide

Setup before class: `streamlit run app.py`, browser at the **Process an invoice** tab, seed 42, Ollama toggle OFF (fallback is the default; nothing to fail).

| Time | Do | Say |
|---|---|---|
| 0:00–0:30 | Show **Dashboard** | "AP teams match invoice to PO and goods receipt. Exceptions are diagnosed by hand. 63 synthetic invoices, 13 anomaly types. Everything is simulated." Point at 23 auto-approved / 40 to humans, 100% vs generator labels (state the caveat). |
| 0:30–1:30 | Process tab → pick **"Duplicate invoice (re-formatted number)"** → Run agents | Open **1 Plan** ("Planner chose these tasks"), **2 Timeline** (agent order), **4 Tool calls** (duplicate_check matched `aos 12345` to `AOS-12345`). |
| 1:30–2:15 | Explain decision | Banner: REJECT; **3 Evidence** shows clause AP-5 retrieved; **5 Critic**: all 8 ✅ from raw data. |
| 2:15–3:15 | Pick **"Billed more than received"** → Run | PAY_PARTIAL: show 3-way match table, payable < invoice total, "Not paid" amount. |
| 3:15–4:15 | Fault injection → **Transient** → Run | Critic tab: attempt 1 ❌ (K3/K4 mismatch), attempt 2 ✅ — "Orchestrator re-ran Executor+Resolution". Then **Persistent** on duplicate: ESCALATED_CRITIC_FAILURE, payable 0.00. |
| 4:15–4:45 | **Human review** tab → click *Escalate to finance manager* | "Every consequential action is simulated and logged." |
| 4:45–5:00 | **Evaluation** tab | Baseline wrongly auto-approved 30; agents 0. 56 tests passed. Limitations: synthetic data. |

**Fallbacks:** no LLM needed (default). If Streamlit fails, run `python scripts/make_test_matrix.py` and show `docs/test_matrix.md`, or show the PPT screenshots. If the browser is slow, use the pre-selected sample cases above (all deterministic).

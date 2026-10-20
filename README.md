# InvoiceGuard — Agentic Accounts-Payable Exception Resolution (CA-3 PoC)

Multi-agent workflow (Planner · Research · Executor · Resolution · Critic + Orchestrator) that decides what to do with supplier invoices that fail a 3-way match. **All data is synthetic; all payments/emails are simulated.** No paid API, no GPU, no internet needed.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py            # UI
python -m pytest tests -v       # 59 tests
python scripts/make_test_matrix.py   # regenerates docs/test_matrix.md
python -m invoiceguard.data_gen 42 data/synthetic_dataset.json   # dump the dataset
```
App tabs: Problem & solution · Dashboard · Process an invoice (3 one-click demos, live agent trace) · Human review queue · Evaluation · Architecture (diagrams).

Optional: install Ollama and run a model (default `llama3.2`), then tick the sidebar toggle. Without it the app uses a deterministic explanation template.

## Layout
`invoiceguard/` tools · agents · orchestrator · baseline · evaluation · data generator · `policy.json` | `app.py` UI | `tests/` | `docs/` problem statement, architecture, report, demo guide, viva, résumé.

## Honest scope
Synthetic data and simplified rules written by the author; accuracy figures are against generator-written labels, so they validate the PoC logic, not production performance.

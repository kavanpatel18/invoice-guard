"""InvoiceGuard - Streamlit PoC. Run:  streamlit run app.py"""
import copy
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from invoiceguard import tools as T
from invoiceguard.data_gen import LABELS, generate_dataset
from invoiceguard.evaluation import compare, fault_experiment, results_table, run_batch, summary
from invoiceguard.llm import explain
from invoiceguard.orchestrator import (FAULT_PERSISTENT, FAULT_TRANSIENT, REVIEW_ACTIONS, apply_human_review,
                                       process_invoice)

st.set_page_config(page_title="InvoiceGuard - Agentic AP Exception Resolution", page_icon="🧾", layout="wide")
POLICY = T.load_policy()
ROOT = Path(__file__).parent


@st.cache_data(show_spinner=False)
def get_dataset(seed: int) -> dict:
    return generate_dataset(seed)


@st.cache_data(show_spinner=False)
def get_batch(seed: int) -> pd.DataFrame:
    ds = get_dataset(seed)
    return results_table(ds, run_batch(ds, POLICY))


st.title("🧾 InvoiceGuard — Agentic Accounts-Payable Exception Resolution")
st.caption("CA-3 Agentic AI proof of concept · ALL DATA IS SYNTHETIC · every payment/vendor/ERP action is SIMULATED")

with st.sidebar:
    st.header("Synthetic data")
    seed = st.number_input("Dataset seed", 0, 9999, 42, help="Same seed = same dataset = reproducible demo")
    ds = get_dataset(int(seed))
    st.write(f"{len(ds['invoices'])} invoices · {len(ds['pos'])} POs · {len(ds['grns'])} goods receipts · {len(ds['history'])} history records")
    st.download_button("Download dataset (JSON)", json.dumps(ds, indent=1), f"synthetic_dataset_seed{seed}.json", "application/json")
    use_llm = st.toggle("Use local Ollama to rephrase explanation", value=False,
                        help="Optional. Falls back to a deterministic template if Ollama is not running. The LLM never changes numbers or decisions.")
    st.markdown("**Agents:** Planner · Research · Executor · Resolution · Critic  \n**Orchestrator** owns shared state, retries (max 2) and escalation.")

if "reviews" not in st.session_state:
    st.session_state.reviews = {}

tab_dash, tab_proc, tab_queue, tab_eval, tab_arch = st.tabs(
    ["📊 Dashboard", "🔎 Process an invoice", "👤 Human review queue", "🧪 Evaluation", "🏗️ Architecture"])


# ----------------------------------------------------------------------------- helpers
def render_case(state, key: str, show_review: bool = True):
    d = state.decision
    c = st.columns(5)
    c[0].metric("Recommendation", d["decision"])
    c[1].metric("Payable now (INR)", f"{float(d['payable']):,.2f}")
    c[2].metric("Not paid (INR)", f"{float(d['not_paid']):,.2f}")
    c[3].metric("Critic attempts", state.attempts)
    c[4].metric("Status", state.status.replace("_", " ").title())
    text, src = explain(state, POLICY, use_llm)
    st.info(text)
    st.caption(f"Explanation source: {src}. Amounts come from deterministic Python tools; decision from policy rules.")

    t1, t2, t3, t4, t5, t6 = st.tabs(["1 Plan", "2 Agent timeline", "3 Evidence & policy", "4 Tool calls", "5 Critic validation", "6 Human review"])
    with t1:
        st.dataframe(pd.DataFrame(state.plan)[["id", "task", "owner", "depends_on", "status", "rationale"]], hide_index=True, width="stretch")
    with t2:
        st.dataframe(pd.DataFrame(state.audit), hide_index=True, width="stretch")
    with t3:
        ev = state.evidence
        a, b = st.columns(2)
        a.markdown("**Vendor master**"); a.json(ev["vendor"] or {})
        b.markdown("**Purchase order / goods receipt**"); b.json({"po": ev["po"], "grn": ev["grn"]})
        st.markdown("**Policy clauses retrieved for each finding**")
        titles = {x["id"]: x["title"] for x in POLICY["clauses"]}
        st.dataframe(pd.DataFrame([{"finding": k, "clause": v["clause_id"], "title": titles[v["clause_id"]], "retrieval score": v["score"]}
                                   for k, v in d["clauses"].items()]), hide_index=True, width="stretch")
    with t4:
        for call in state.tool_calls:
            with st.expander(f"attempt {call['attempt']} · {call['tool']}({call['args']})"):
                st.json(call["result"])
        m = state.results.get("match")
        if m and m["lines"]:
            st.markdown("**3-way match table**"); st.dataframe(pd.DataFrame(m["lines"]), hide_index=True, width="stretch")
    with t5:
        for i, rep in enumerate(state.critic_history, 1):
            st.markdown(f"**Attempt {i}: {'✅ PASSED' if rep['passed'] else '❌ FAILED'}**")
            df = pd.DataFrame(rep["checks"]); df["passed"] = df["passed"].map({True: "✅", False: "❌"})
            st.dataframe(df, hide_index=True, width="stretch")
        if state.fault_effective:
            st.warning("A fault was injected into the Resolution output; the Critic was responsible for catching it.")
    with t6:
        if state.needs_human and show_review:
            note = st.text_input("Reviewer note (optional)", key=f"note_{key}")
            cols = st.columns(4)
            for col, act in zip(cols, REVIEW_ACTIONS):
                if col.button(act, key=f"{key}_{act}"):
                    apply_human_review(state, act, note)
                    st.session_state.reviews[state.invoice.get("invoice_id", "custom")] = {
                        "invoice_id": state.invoice.get("invoice_id", "custom"), "recommendation": d["decision"],
                        "action": act, "note": note, **{"simulated_effect": state.human_review["simulated_effect"],
                                                         "time": state.human_review["time"]}}
                    st.success(state.human_review["simulated_effect"])
        elif not state.needs_human:
            st.success("Auto-approved (simulated): clean match, below approval limit, Critic passed. No human action needed.")
        r = st.session_state.reviews.get(state.invoice.get("invoice_id", "custom"))
        if r:
            st.write("Recorded decision:", r["action"], "—", r["simulated_effect"])


def invoice_options():
    return {f"{i['invoice_id']} · {ds['vendors'][i['vendor_id']]['name']} · {ds['ground_truth'][i['invoice_id']]['label']}": i for i in ds["invoices"]}


# ----------------------------------------------------------------------------- dashboard
with tab_dash:
    df = get_batch(int(seed)); m = summary(df)
    c = st.columns(6)
    c[0].metric("Invoices processed", m["cases"]); c[1].metric("Decision accuracy*", f"{m['decision_accuracy']}%")
    c[2].metric("Payable-amount accuracy*", f"{m['payable_accuracy']}%"); c[3].metric("Auto-approved", m["auto_approved"])
    c[4].metric("Sent to human review", m["human_review"]); c[5].metric("Avg time / case", f"{m['avg_ms']} ms")
    st.caption("*Measured against ground-truth labels written by the synthetic-data generator. This validates the PoC logic, not real-world accuracy.")
    a, b = st.columns(2)
    a.subheader("Decisions"); a.bar_chart(df.decision.value_counts())
    b.subheader("Cases by detected anomaly"); b.bar_chart(df.groupby("scenario").size())
    flt = st.multiselect("Filter by decision", sorted(df.decision.unique()), default=[])
    view = df[df.decision.isin(flt)] if flt else df
    st.dataframe(view, hide_index=True, width="stretch")
    st.download_button("Download results CSV", df.to_csv(index=False), "invoiceguard_results.csv", "text/csv")

# ----------------------------------------------------------------------------- process
with tab_proc:
    mode = st.radio("Invoice source", ["Sample scenario", "Build a custom invoice"], horizontal=True)
    fault_name = st.selectbox("Fault injection (demonstrates the Critic)", ["None", "Transient wrong payable (fixed on retry)", "Persistent wrong approval (must escalate)"])
    fault = {"None": None}.get(fault_name) or (FAULT_TRANSIENT if fault_name.startswith("Transient") else FAULT_PERSISTENT)
    inv = None
    if mode == "Sample scenario":
        opts = invoice_options()
        pick = st.selectbox("Choose a sample case", list(opts))
        inv = opts[pick]
        with st.expander("Invoice document"):
            st.json(inv)
    else:
        po_id = st.selectbox("Purchase order", list(ds["pos"]))
        po = ds["pos"][po_id]; vend = ds["vendors"][po["vendor_id"]]
        c1, c2, c3 = st.columns(3)
        no = c1.text_input("Invoice number", "CUSTOM-0001"); dt = c2.text_input("Invoice date (YYYY-MM-DD)", "2026-09-20")
        bank = c3.text_input("Bank account on invoice", vend["bank_account"])
        tax = st.number_input("Tax rate", 0.0, 1.0, 0.18 if vend["gst_registered"] else 0.0, 0.01)
        lines = st.data_editor(pd.DataFrame([{"sku": l["sku"], "qty": l["qty"], "unit_price": l["unit_price"]} for l in po["lines"]]),
                               num_rows="dynamic", width="stretch", key=f"ed_{po_id}")
        inv = {"invoice_id": "CUSTOM", "invoice_no": no, "vendor_id": po["vendor_id"], "po_id": po_id, "invoice_date": dt,
               "lines": lines.dropna().to_dict("records"), "tax_rate": tax, "bank_account": bank}
        try:
            auto = float(T.invoice_total(inv)) if inv["lines"] else 0.0
        except Exception:
            auto = 0.0
        inv["declared_total"] = st.number_input("Declared total (change it to trigger an arithmetic error)", 0.0, 1e9, auto)
    if st.button("▶ Run agents", type="primary"):
        try:
            st.session_state.case = process_invoice(copy.deepcopy(inv), ds, POLICY, fault)
            st.session_state.case_key = f"{inv.get('invoice_id')}_{fault_name}"
        except ValueError as e:
            st.error(str(e))
    if "case" in st.session_state:
        render_case(st.session_state.case, "proc_" + st.session_state.case_key)

# ----------------------------------------------------------------------------- queue
with tab_queue:
    df = get_batch(int(seed)); q = df[df.needs_human]
    st.write(f"{len(q)} of {len(df)} invoices need human sign-off. Pick one, review the agents' reasoning, then act (all actions simulated).")
    pick = st.selectbox("Case", [f"{r.invoice_id} · {r.decision} · {r.scenario}" for r in q.itertuples()], key="qpick")
    if pick:
        iid = pick.split(" · ")[0]
        s = process_invoice(next(i for i in ds["invoices"] if i["invoice_id"] == iid), ds, POLICY)
        render_case(s, "q_" + iid)
    if st.session_state.reviews:
        st.subheader("Review log"); rv = pd.DataFrame(st.session_state.reviews.values())
        st.dataframe(rv, hide_index=True, width="stretch")
        st.download_button("Download review log CSV", rv.to_csv(index=False), "human_review_log.csv", "text/csv")

# ----------------------------------------------------------------------------- evaluation
with tab_eval:
    df = get_batch(int(seed))
    st.subheader("Agents vs. baseline (same synthetic data)")
    st.dataframe(compare(ds, df), hide_index=True, width="stretch")
    st.caption("Baseline = naive 2-way match (invoice subtotal vs PO subtotal within 2%): no goods-receipt, duplicate, bank, GST or limit checks.")
    st.subheader("Accuracy by scenario")
    st.dataframe(df.groupby("scenario").agg(cases=("correct", "size"), decision_correct=("correct", "sum"), payable_correct=("payable_ok", "sum")).reset_index(),
                 hide_index=True, width="stretch")
    st.subheader("Fault-injection experiment")
    kind = st.radio("Fault", ["transient", "persistent"], horizontal=True)
    if st.button("Run fault experiment on all invoices"):
        f = fault_experiment(ds, kind); e = f[f.fault_effective]
        c = st.columns(4)
        c[0].metric("Faults that changed the output", len(e)); c[1].metric("Detected by Critic (1st attempt)", f"{int(e.detected_first_attempt.sum())}/{len(e)}")
        c[2].metric("Final output correct" if kind == "transient" else "Safe outcome (no over-payment)", f"{int((e.final_correct if kind == 'transient' else e.safe_outcome).sum())}/{len(e)}")
        c[3].metric("Unsafe payments released", int(e.unsafe_payment_released.sum()))
        st.dataframe(f, hide_index=True, width="stretch")
        st.download_button("Download fault experiment CSV", f.to_csv(index=False), f"fault_{kind}.csv", "text/csv")
    mx = ROOT / "docs" / "test_matrix.md"
    if mx.exists():
        with st.expander("Test matrix (generated by scripts/make_test_matrix.py)"):
            st.markdown(mx.read_text(encoding="utf-8"))

# ----------------------------------------------------------------------------- architecture
with tab_arch:
    st.markdown("""
| Agent | Responsibility | Type of logic |
|---|---|---|
| **Planner** | Builds a state-dependent task plan with dependencies | rules |
| **Research** | Fetches vendor/PO/GRN/history; retrieves policy clauses (IDF keyword retrieval) | retrieval |
| **Executor** | Runs deterministic tools: validation, duplicate, bank, GST, 3-way match, payable | Python (Decimal) |
| **Resolution** | Maps findings to APPROVE / PAY_PARTIAL / HOLD / REJECT / ESCALATE by priority rules | rules |
| **Critic** | Re-derives findings, decision & amount from raw data with exact fractions; 8 checks | independent code |
| **Orchestrator** | Shared state, bounded retries (2), escalation, human routing, audit log | control logic |
""")
    md = ROOT / "docs" / "architecture.md"
    if md.exists():
        st.markdown("**Mermaid source** (paste into https://mermaid.live to view/edit; also rendered in docs/architecture.md on GitHub)")
        st.code(md.read_text(encoding="utf-8").split("```mermaid")[1].split("```")[0].strip(), language="text")

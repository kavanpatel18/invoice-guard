# Architecture (matches the code in `invoiceguard/`)

## 1. Component diagram

```mermaid
flowchart TD
  U([Evaluator / AP clerk]) --> UI["Streamlit UI (app.py)<br/>Dashboard · Process · Review queue · Evaluation"]
  UI -->|"invoice + optional fault toggle"| ORC["Orchestrator (orchestrator.py)<br/>process_invoice() + shared CaseState"]
  DS[("Synthetic dataset<br/>vendors · POs · GRNs · history · invoices<br/>data_gen.py, seeded")] --> RES
  POL[("policy.json<br/>parameters + 9 clauses")] --> EXE
  POL --> RSV
  POL --> CRT
  ORC -->|1| PLN["Planner Agent<br/>state-dependent task plan"]
  PLN -->|plan| ORC
  ORC -->|2| RES["Research Agent<br/>fetch vendor/PO/GRN/history"]
  RES -->|evidence| ORC
  ORC -->|3| EXE["Executor Agent"]
  EXE --> TLS["Deterministic tools (tools.py, Decimal)<br/>validate_input · duplicate_check · bank_check<br/>tax_check · three_way_match · payable_amount"]
  TLS -->|findings + amounts| ORC
  ORC -->|4| RSV["Resolution Agent<br/>priority rules → APPROVE / PAY_PARTIAL / HOLD / REJECT / ESCALATE"]
  RSV -->|decision| CITE["Research Agent<br/>policy-clause retrieval (IDF keyword)"]
  FLT{{"Fault injector<br/>(demo/test only)"}} -.->|corrupts output| RSV
  CITE --> ORC
  ORC -->|5| CRT["Critic Agent<br/>8 checks, re-derives from RAW data<br/>exact fractions, own logic"]
  DS --> CRT
  CRT -->|PASS| RT{"decision == APPROVE?"}
  CRT -->|"FAIL & attempt < 2"| ORC
  CRT -->|"FAIL & attempt = 2"| ESC["Escalate: payable = 0<br/>ESCALATED_CRITIC_FAILURE"]
  RT -->|yes| AUTO["Auto-approve (SIMULATED)"]
  RT -->|no| HUM["Human review queue<br/>accept · reject · request info · escalate (SIMULATED)"]
  ESC --> HUM
  AUTO --> AUD[("Audit log + tool-call log<br/>inside CaseState")]
  HUM --> AUD
  AUD --> REP["Reports: dashboard, results CSV,<br/>review log CSV, fault-experiment CSV"]
  REP --> UI
```

## 2. Sequence (one invoice)

```mermaid
sequenceDiagram
  participant UI as Streamlit
  participant O as Orchestrator
  participant P as Planner
  participant R as Research
  participant E as Executor
  participant S as Resolution
  participant C as Critic
  participant H as Human
  UI->>O: process_invoice(invoice, fault?)
  O->>P: plan(invoice)
  P-->>O: tasks T1..Tn (+dependencies)
  O->>R: gather(invoice)
  R-->>O: vendor, PO, GRN, history
  loop attempt = 1..2
    O->>E: run(plan) → tool calls
    E-->>O: findings, invoice_total, prospective_payable
    O->>S: decide(findings)
    S-->>O: decision, payable, reasons
    O->>R: cite(reasons) → policy clauses
    O->>C: review(raw data, decision)
    C-->>O: 8 checks (pass / fail)
  end
  alt Critic passed and APPROVE
    O-->>UI: AUTO_APPROVED_SIMULATED
  else Critic passed, other decision
    O-->>H: PENDING_HUMAN_REVIEW
  else Critic failed twice
    O-->>H: ESCALATED_CRITIC_FAILURE (payable 0)
  end
  H-->>O: action (simulated effect logged)
```

## 3. Components and interactions

| Component | File | Input → Output | Failure behaviour |
|---|---|---|---|
| Streamlit UI | `app.py` | user choices → renders `CaseState` | invalid vendor → clear error message |
| Orchestrator | `orchestrator.py` | invoice, dataset → `CaseState` | max 2 attempts, then escalate with payable 0 |
| Planner | `agents.py` | invoice → task list | invalid invoice → shortened plan (validate → decide → critic → route) |
| Research | `agents.py` | invoice → evidence; finding codes → clause ids | missing PO/GRN returned as `None` and handled downstream |
| Executor | `agents.py` + `tools.py` | plan + evidence → findings, amounts | every tool call logged in `tool_calls` |
| Resolution | `agents.py` | findings → decision | first matching finding by priority wins |
| Critic | `agents.py` | raw data + decision → 8 checks | any failed check blocks the decision |
| Fault injector | `orchestrator._inject` | decision → corrupted decision | used only for demo/tests |
| Baseline | `baseline.py` | invoice → APPROVE / MANUAL | comparison only |

## 4. Decision priority (Resolution Agent and Critic implement it separately)
`INPUT_INVALID→HOLD` > `BANK_MISMATCH→ESCALATE` > `DUPLICATE_INVOICE→REJECT` > `NO_PO / SKU_NOT_ON_PO→HOLD` > `NO_GRN→HOLD` > `TAX_RATE_MISMATCH→HOLD` > `PRICE_OVER_TOLERANCE→HOLD` > payable above limit → `ESCALATE` > `QTY_OVER_RECEIVED→PAY_PARTIAL` > `APPROVE`.

## 5. What is LLM / rules / code / retrieval / human
| Element | Kind |
|---|---|
| Plan, decision, routing | rule-based Python |
| Amounts, matching, duplicates, GST | deterministic Python (Decimal) |
| Critic re-derivation | independent Python (exact fractions) |
| Policy clause lookup | retrieval (IDF-weighted keyword overlap) |
| Explanation text | deterministic template; optional local Ollama rephrase (numbers verified, falls back if not matching) |
| Final consequential action | human review (simulated) |

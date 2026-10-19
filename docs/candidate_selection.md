# Phase 1 - Candidate problems and weighted scoring

Scores are **my own judgement** against the CA-3 weighting model (not measured data). Scores reflect how well each idea fits the rubric *within a ~1-week build using only Python/Streamlit and synthetic data*.

| Candidate                                                      |   Originality (15) |   Business problem (15) |   Agentic fit (20) |   Tech depth / résumé (15) |   Feasibility (10) |   Measurability (10) |   Demo reliability (10) |   Synthetic data (5) |   Total /100 |
|:---------------------------------------------------------------|-------------------:|------------------------:|-------------------:|---------------------------:|-------------------:|---------------------:|------------------------:|---------------------:|-------------:|
| 1. AP invoice exception resolution (Finance)                   |                 12 |                      14 |                 18 |                         13 |                  9 |                   10 |                       9 |                    5 |           90 |
| 3. Loan KYC document discrepancy resolution (Banking)          |                 10 |                      14 |                 16 |                         13 |                  7 |                    8 |                       7 |                    4 |           79 |
| 5. Shipment-disruption re-planning (Supply chain)              |                 12 |                      13 |                 15 |                         14 |                  6 |                    7 |                       6 |                    4 |           77 |
| 2. Hospital claim-denial triage & appeal drafting (Healthcare) |                 11 |                      14 |                 16 |                         13 |                  6 |                    7 |                       6 |                    3 |           76 |
| 8. Exam timetable clash resolution (Education)                 |                 10 |                       9 |                 12 |                         13 |                  8 |                    9 |                       8 |                    5 |           74 |
| 4. Retail returns/refund fraud decisioning (E-commerce)        |                  8 |                      11 |                 13 |                         10 |                  9 |                    8 |                       9 |                    5 |           73 |
| 7. Support-ticket refund resolution (Customer support)         |                  7 |                      11 |                 14 |                         10 |                  9 |                    8 |                       9 |                    5 |           73 |
| 9. Maintenance work-order planning (Manufacturing)             |                 11 |                      12 |                 14 |                         13 |                  6 |                    6 |                       6 |                    4 |           72 |
| 6. Resume screening + interview scheduling (HR)                |                  6 |                      10 |                 11 |                          9 |                  9 |                    6 |                       9 |                    5 |           65 |

## Why #1 won
* **Decision-intensive, not conversational:** five distinct outcomes (approve / pay partially / hold / reject / escalate) governed by explicit priority rules.
* **Agents are justified:** retrieval of records + policy, deterministic tool execution, rule-based resolution and an *independent* Critic are genuinely different jobs; a single prompt could not provide the independent check that money-moving decisions need.
* **Measurable with synthetic ground truth:** the generator injects 13 anomaly types with known correct outcomes, so accuracy, error detection and a baseline comparison can be computed, not asserted.
* **Reliable live demo:** fully deterministic, runs in milliseconds, no API or GPU needed.
* **Real-world grounding (verified):** FBI IC3's 2024 report lists business email compromise (bank-detail fraud) at about USD 2.8 billion in reported losses from 21,442 complaints (summarised by Nacha, 24 Apr 2025: https://www.nacha.org/news/fbis-ic3-finds-almost-85-billion-lost-business-email-compromise-last-three-years). This is why a vendor-bank-change control is a core rule. All other business parameters (2% tolerance, INR 5,00,000 limit, 18% GST) are **illustrative assumptions**, not verified industry statistics.

## Why not the others
Claim denial and supply-chain re-planning need deep domain rules/data that are hard to synthesise credibly; HR screening and support bots drift towards "chatbot with a title"; timetabling is mostly a constraint solver rather than an agent workflow.

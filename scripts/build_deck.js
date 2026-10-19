const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/mnt/skills/public/pptx/scripts/apply_theme.js");
const THEME = { name: "InvoiceGuard", headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: "111827", lt1: "FFFFFF", dk2: "1E3A5F", lt2: "EEF3F8", accent1: "0F766E", accent2: "2563EB",
    accent3: "B45309", accent4: "B91C1C", accent5: "6D28D9", accent6: "15803D", hlink: "2563EB", folHlink: "6D28D9" } };
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "InvoiceGuard - CA-3 Agentic AI PoC";
pres.author = "Kavan";
const C = pres.SchemeColor;

pres.defineSlideMaster({ title: "TITLE_DARK", objects: [
  { rect: { x: 0, y: 0, w: 10, h: 5.625, fill: { color: C.text2 } } },
  { rect: { x: 0, y: 0, w: 0.25, h: 5.625, fill: { color: C.accent1 } } } ],
  slideNumber: undefined });
pres.defineSlideMaster({ title: "CONTENT",
  background: { color: "FFFFFF" },
  objects: [
    { rect: { x: 0, y: 0, w: 10, h: 0.08, fill: { color: C.accent1 } } },
    { text: { text: "InvoiceGuard · synthetic data · all actions simulated", options: { x: 0.5, y: 5.25, w: 6, h: 0.25, fontSize: 9, color: C.text1, margin: 0 } } } ],
  slideNumber: { x: 9.2, y: 5.25, w: 0.4, h: 0.25, fontSize: 9, color: C.text1 },
  placeholders: [{ placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.25, w: 9, h: 0.85, fontSize: 24, bold: true, color: C.text2, align: "left", valign: "middle", margin: 0 }, text: "" } }] });

const TO = () => ({ x: 0.5, y: 0.3, w: 9, h: 0.8, fontSize: 24, bold: true, color: C.text2, valign: "middle", align: "left", margin: 0, isTextBox: true });
const card = (s, x, y, w, h, big, small, col) => {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: "card " + big });
  s.addText(big, { x: x + 0.15, y: y + 0.1, w: w - 0.3, h: h * 0.45, fontSize: 28, bold: true, color: col, margin: 0, isTextBox: true, valign: "middle" });
  s.addText(small, { x: x + 0.15, y: y + h * 0.55, w: w - 0.3, h: h * 0.4, fontSize: 11, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
};
const box = (s, x, y, w, h, text, fill, fs = 11, tc = C.background1, bold = false) =>
  s.addText(text, { x, y, w, h, shape: pres.ShapeType.roundRect, rectRadius: 0.06, fill: { color: fill }, color: tc, fontSize: fs, bold, align: "center", valign: "middle", margin: 0.04, objectName: "box " + text.slice(0, 18) });
const line = (s, x, y, w, h) => s.addShape(pres.ShapeType.line, { x, y, w, h, line: { color: C.text1, width: 1.25, endArrowType: "triangle" }, objectName: "arrow" });

// 1 ---- title
pres.addSection({ title: "Problem" });
let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Problem" });
s.addText("InvoiceGuard", { x: 0.7, y: 1.3, w: 8.5, h: 0.9, fontSize: 44, bold: true, color: C.background1, margin: 0, isTextBox: true });
s.addText("Agentic AI for Accounts-Payable exception resolution", { x: 0.7, y: 2.2, w: 8.5, h: 0.6, fontSize: 22, color: C.background1, margin: 0, isTextBox: true });
s.addText("Domain: Finance operations  ·  CA-3 Agentic AI PoC  ·  SIT Pune", { x: 0.7, y: 3.2, w: 8.5, h: 0.4, fontSize: 14, color: C.background2, margin: 0, isTextBox: true });
s.addText("Presented by Kavan  ·  Python + Streamlit  ·  synthetic data only", { x: 0.7, y: 3.65, w: 8.5, h: 0.4, fontSize: 14, color: C.background2, margin: 0, isTextBox: true });
s.addNotes("[0:00-0:20] Hello. InvoiceGuard is a multi-agent system that decides what to do with supplier invoices that fail a 3-way match. Everything you will see uses synthetic data and simulated actions.");

// 2 ---- problem
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem" });
s.addText("Mismatched invoices are costly, and a total-only check misses most of the reasons", TO());
s.addText([
  { text: "Companies pay only after matching invoice, purchase order and goods receipt.", options: { bullet: true, breakLine: true } },
  { text: "Exceptions are diagnosed by hand: open PO, GRN, vendor, history and policy, then email the vendor.", options: { bullet: true, breakLine: true } },
  { text: "Hard cases: duplicates with a re-formatted number, goods not received, wrong GST, and changed bank details (a fraud pattern).", options: { bullet: true } }],
  { x: 0.5, y: 1.35, w: 4.6, h: 3.4, fontSize: 15, color: C.text1, paraSpaceAfter: 10, valign: "top", margin: 0, isTextBox: true });
card(s, 5.4, 1.35, 4.1, 1.15, "30 of 53", "invoices wrongly auto-approved by a naive 2-way match (measured on our synthetic set)", C.accent4);
card(s, 5.4, 2.65, 4.1, 1.15, "≈ $2.8 B", "business-email-compromise losses reported to FBI IC3 in 2024 (source: Nacha summary)", C.accent3);
card(s, 5.4, 3.95, 4.1, 1.05, "13", "synthetic anomaly types with known correct outcomes", C.accent1);
s.addNotes("[0:20-0:55] AP clerks match invoice, PO and goods receipt. Exceptions are slow and inconsistent. On our synthetic data a total-only rule wrongly auto-approved 30 of the 53 invoices it approved. The $2.8B figure is FBI IC3's 2024 reported BEC loss, which is why bank-detail changes are a core control.");

// 3 ---- existing vs proposed
pres.addSection({ title: "Solution" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Solution" });
s.addText("From manual exception queues to a planned, checked and auditable workflow", TO());
s.addText("TODAY", { x: 0.5, y: 1.3, w: 2, h: 0.3, fontSize: 12, bold: true, color: C.accent4, margin: 0, isTextBox: true });
["Invoice arrives", "Total-only match", "Manual queue", "Clerk investigates", "Email vendor"].forEach((t, i) =>
  box(s, 0.5 + i * 1.82, 1.65, 1.6, 0.7, t, C.accent4, 12));
s.addText("INVOICEGUARD", { x: 0.5, y: 2.75, w: 3, h: 0.3, fontSize: 12, bold: true, color: C.accent1, margin: 0, isTextBox: true });
["Plan", "Research", "Execute tools", "Decide", "Critic check", "Auto / human"].forEach((t, i) =>
  box(s, 0.5 + i * 1.52, 3.1, 1.35, 0.7, t, C.accent1, 12));
s.addText("Five outcomes: APPROVE · PAY_PARTIAL · HOLD · REJECT · ESCALATE. Failed validation retries once, then blocks payment and escalates. Humans approve every non-clean case.",
  { x: 0.5, y: 4.15, w: 9, h: 0.8, fontSize: 14, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
s.addNotes("[0:55-1:30] Today: total-only match, then a human does the investigation. InvoiceGuard plans which checks apply, retrieves records and policy, runs exact calculations, decides, and has an independent Critic verify before anything happens. Five possible outcomes; only clean invoices below the limit auto-approve.");

// 4 ---- architecture
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Solution" });
s.addText("Agent architecture: five agents coordinated by one orchestrator", TO());
box(s, 0.5, 1.25, 1.7, 0.55, "Streamlit UI", C.accent2, 12, C.background1, true);
box(s, 2.6, 1.25, 4.8, 0.55, "Orchestrator · shared CaseState · retry ≤ 2 · audit log", C.text2, 12, C.background1, true);
box(s, 7.8, 1.25, 1.7, 0.55, "Human reviewer", C.accent3, 12, C.background1, true);
line(s, 2.2, 1.52, 0.4, 0); line(s, 7.8, 1.52, -0.4, 0);
s.addShape(pres.ShapeType.line, { x: 1.3, y: 2.05, w: 7.4, h: 0, line: { color: C.text1, width: 1.25 }, objectName: "bus" });
line(s, 5.0, 1.8, 0, 0.25);
const ag = [["Planner", "task plan with dependencies"], ["Research", "records + policy clause retrieval"], ["Executor", "6 deterministic tools (Decimal)"], ["Resolution", "priority rules + decision"], ["Critic", "8 checks from raw data (fractions)"]];
ag.forEach((a, i) => {
  const x = 0.5 + i * 1.82;
  line(s, x + 0.8, 2.05, 0, 0.25);
  box(s, x, 2.3, 1.62, 0.55, a[0], C.accent1, 13, C.background1, true);
  box(s, x, 2.95, 1.62, 0.75, a[1], C.background2, 10.5, C.text1);
});
s.addText("Data: synthetic vendors · POs · goods receipts · invoice history · policy.json (9 clauses)", { x: 0.5, y: 3.85, w: 9, h: 0.3, fontSize: 11, color: C.text1, align: "center", margin: 0, isTextBox: true });
box(s, 0.5, 4.3, 2.8, 0.6, "Critic PASS + clean: auto-approve (simulated)", C.accent6, 11);
box(s, 3.6, 4.3, 2.8, 0.6, "Critic PASS + exception: human queue", C.accent3, 11);
box(s, 6.7, 4.3, 2.8, 0.6, "Critic FAIL twice: escalate, payable 0", C.accent4, 11);
s.addNotes("[1:30-2:10] The orchestrator owns shared state. Planner builds the plan, Research fetches records and cites policy, Executor runs exact tools, Resolution applies priority rules, and the Critic re-derives everything from raw data. Three exits at the bottom: auto-approve, human queue, or escalate with payment blocked.");

// 5 ---- responsibilities table
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Solution" });
s.addText("Each agent has a distinct job; decisions use rules, not an LLM", TO());
const hdr = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text2 }, fontSize: 12 } });
const cell = (t, b) => ({ text: t, options: { fontSize: 11, color: C.text1, bold: !!b } });
s.addTable([
  [hdr("Agent"), hdr("Responsibility"), hdr("Logic type")],
  [cell("Planner", 1), cell("Builds task plan; shortens it for invalid invoices; picks 3-way match or missing-PO flag"), cell("rules")],
  [cell("Research", 1), cell("Fetches vendor, PO, GRN, history; retrieves the policy clause behind each finding"), cell("retrieval")],
  [cell("Executor", 1), cell("Validation, duplicate, bank, GST, 3-way match, payable amount; logs every tool call"), cell("Python (Decimal)")],
  [cell("Resolution", 1), cell("Maps findings to one decision by priority; bank change outranks over-billing"), cell("rules")],
  [cell("Critic", 1), cell("Independent re-derivation; blocks wrong decisions, amounts or skipped controls"), cell("independent code")],
  [cell("Orchestrator", 1), cell("Shared state, retry up to 2, escalation, routing, audit log"), cell("control logic")]],
  { x: 0.5, y: 1.3, w: 9, colW: [1.5, 5.9, 1.6], rowH: 0.5, border: { type: "solid", color: "D1D5DB", pt: 0.75 }, valign: "middle", autoPage: false });
s.addNotes("[2:10-2:40] Distinct responsibilities, no duplicates. The only place text is generated is an optional local-LLM rephrase; it never touches numbers or decisions.");

// 6 ---- demo
pres.addSection({ title: "Evidence" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
s.addText("Live demo (about 80 seconds): the same app, three cases", TO());
const steps = [["1", "Duplicate invoice", "Number re-formatted as 'aos 12345'. Tool call matches it; clause AP-5 cited; REJECT."],
  ["2", "Billed more than received", "3-way match table; PAY_PARTIAL with exact payable and amount not paid."],
  ["3", "Fault injection", "Transient: Critic fails attempt 1, fixed on retry. Persistent: escalated, payable 0.00."]];
steps.forEach((t, i) => {
  const y = 1.35 + i * 1.15;
  s.addShape(pres.ShapeType.ellipse, { x: 0.5, y: y + 0.1, w: 0.6, h: 0.6, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: "step " + t[0] });
  s.addText(t[0], { x: 0.5, y: y + 0.1, w: 0.6, h: 0.6, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addText(t[1], { x: 1.3, y, w: 3.0, h: 0.8, fontSize: 16, bold: true, color: C.text2, valign: "middle", margin: 0, isTextBox: true });
  s.addText(t[2], { x: 4.3, y, w: 5.2, h: 0.8, fontSize: 13, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
});
s.addText("Then: human review tab (accept / reject / request info / escalate, all simulated) and the Evaluation tab.", { x: 0.5, y: 4.85, w: 9, h: 0.3, fontSize: 12, color: C.text1, margin: 0, isTextBox: true });
s.addNotes("[2:40-4:00] SWITCH TO THE APP. Process tab. (1) Pick the duplicate case: open Plan, Tool calls, Evidence (clause AP-5), Critic (8 green checks). (2) Pick 'Billed more than received': show the match table and payable. (3) Fault injection: Transient, then Persistent on the duplicate. End with the human-review button. Fallback: docs/test_matrix.md shows the same cases.");

// 7 ---- results
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
s.addText("Measured results on 63 synthetic invoices (seed 42)", TO());
s.addChart(pres.charts.BAR, [{ name: "Wrongly auto-approved", labels: ["Baseline 2-way match", "InvoiceGuard"], values: [30, 0] }],
  { x: 0.5, y: 1.25, w: 4.4, h: 3.6, barDir: "col", chartColors: ["B91C1C", "0F766E"], showTitle: true, title: "Invoices wrongly auto-approved", titleFontSize: 12, titleColor: "111827",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 12, showLegend: false, valGridLine: { color: "E5E7EB", size: 0.5 }, catGridLine: { style: "none" },
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", catAxisLabelFontSize: 11, valAxisLabelFontSize: 10, valAxisMaxVal: 35, varyColors: true });
card(s, 5.2, 1.25, 2.05, 1.1, "56 / 56", "automated tests passed", C.accent1);
card(s, 7.45, 1.25, 2.05, 1.1, "19 / 19", "test-matrix scenarios", C.accent1);
card(s, 5.2, 2.5, 2.05, 1.1, "63 / 63", "decisions and payable amounts match labels", C.accent2);
card(s, 7.45, 2.5, 2.05, 1.1, "0", "payments released under persistent fault", C.accent6);
s.addText("Injected faults: 63/63 caught (transient, all fixed on retry); 40/40 caught (persistent, all escalated). Labels come from our own generator, so this shows consistency, not real-world accuracy.",
  { x: 5.2, y: 3.75, w: 4.3, h: 1.2, fontSize: 12, color: C.text1, margin: 0, isTextBox: true, valign: "top" });
s.addNotes("[4:00-4:40] 56 tests and a 19-scenario matrix all pass. Against the baseline, 30 wrong auto-approvals versus 0. Fault injection: every effective fault was detected. Caveat: labels come from my generator, so this proves the logic is consistent, not that it would score 100% on real invoices.");

// 8 ---- limits
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
s.addText("Limitations, future scope and conclusion", TO());
s.addText("Limitations", { x: 0.5, y: 1.3, w: 4.3, h: 0.3, fontSize: 15, bold: true, color: C.accent4, margin: 0, isTextBox: true });
s.addText([{ text: "Synthetic data, simplified policy", options: { bullet: true, breakLine: true } }, { text: "No OCR, ERP or bank integration", options: { bullet: true, breakLine: true } },
  { text: "Critic shares policy parameters with Executor", options: { bullet: true, breakLine: true } }, { text: "Single currency, in-session review log", options: { bullet: true } }],
  { x: 0.5, y: 1.65, w: 4.3, h: 2.0, fontSize: 13, color: C.text1, paraSpaceAfter: 6, valign: "top", margin: 0, isTextBox: true });
s.addText("Future scope (not built)", { x: 5.2, y: 1.3, w: 4.3, h: 0.3, fontSize: 15, bold: true, color: C.accent1, margin: 0, isTextBox: true });
s.addText([{ text: "Invoice PDF ingestion (OCR)", options: { bullet: true, breakLine: true } }, { text: "LangGraph orchestration, MCP ERP tools", options: { bullet: true, breakLine: true } },
  { text: "Learn thresholds from clerk overrides", options: { bullet: true, breakLine: true } }, { text: "Authentication and role-based approval", options: { bullet: true } }],
  { x: 5.2, y: 1.65, w: 4.3, h: 2.0, fontSize: 13, color: C.text1, paraSpaceAfter: 6, valign: "top", margin: 0, isTextBox: true });
s.addShape(pres.ShapeType.roundRect, { x: 0.5, y: 3.85, w: 9, h: 1.0, rectRadius: 0.08, fill: { color: C.text2 }, line: { color: C.text2 }, objectName: "conclusion band" });
s.addText("An independent Critic, bounded retries and human approval turn plain automation into a workflow you can trust with money-related decisions.",
  { x: 0.75, y: 3.9, w: 8.5, h: 0.9, fontSize: 15, bold: true, color: C.background1, valign: "middle", margin: 0, isTextBox: true });
s.addNotes("[4:40-5:00] Limitations are honest: synthetic data and simplified rules. Next steps would be OCR and real ERP integration. Takeaway: independent validation plus human approval. Thank you; happy to take questions.");

(async () => {
  await pres.writeFile({ fileName: "InvoiceGuard_CA3.pptx" });
  await applyTheme("InvoiceGuard_CA3.pptx", THEME);
  console.log("ok");
})();

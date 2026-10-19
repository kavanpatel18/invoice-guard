"""The five agents. Each has one responsibility and communicates only through CaseState."""
from __future__ import annotations

import math
import re
from decimal import Decimal
from fractions import Fraction

from . import tools as T

DECISION_BY_FINDING = {  # priority order = order of this list (first match wins)
    "INPUT_INVALID": "HOLD", "BANK_MISMATCH": "ESCALATE", "DUPLICATE_INVOICE": "REJECT",
    "NO_PO": "HOLD", "SKU_NOT_ON_PO": "HOLD", "NO_GRN": "HOLD", "TAX_RATE_MISMATCH": "HOLD",
    "PRICE_OVER_TOLERANCE": "HOLD",
}
FINDING_QUERY = {
    "INPUT_INVALID": "invoice missing mandatory fields or arithmetic error in declared total",
    "BANK_MISMATCH": "bank account on invoice differs from vendor master record",
    "DUPLICATE_INVOICE": "duplicate invoice with same number already processed",
    "NO_PO": "invoice without purchase order reference",
    "SKU_NOT_ON_PO": "invoice bills an item that is not on the purchase order",
    "NO_GRN": "no goods receipt note posted for the order",
    "TAX_RATE_MISMATCH": "GST tax rate charged differs from vendor registration",
    "PRICE_OVER_TOLERANCE": "unit price above purchase order price tolerance",
    "QTY_OVER_RECEIVED": "quantity billed exceeds quantity received",
    "OVER_APPROVAL_LIMIT": "payable amount exceeds approval limit needs manager sign-off",
}


def _task(i, name, owner, deps, why):
    return {"id": f"T{i}", "task": name, "owner": owner, "depends_on": deps, "status": "pending", "rationale": why}


# =============================================================== 1. Planner
class PlannerAgent:
    """Builds an explicit, state-dependent task plan (rule-based; no LLM needed)."""
    name = "Planner"

    def plan(self, inv: dict, dataset: dict, params: dict) -> list[dict]:
        tasks = [_task(1, "validate_input", "Executor", [], "Every invoice is checked for completeness/arithmetic first")]
        if T.validate_input(inv, params)["valid"]:
            tasks += [
                _task(2, "duplicate_check", "Executor", ["T1"], "Fraud/duplicate control against invoice history"),
                _task(3, "bank_check", "Executor", ["T1"], "Compare bank account with vendor master"),
                _task(4, "tax_check", "Executor", ["T1"], "GST rate must match vendor registration"),
            ]
            if inv.get("po_id") and inv["po_id"] in dataset["pos"]:
                tasks.append(_task(5, "three_way_match", "Executor", ["T1"], "PO exists: match invoice vs PO vs goods receipt"))
            else:
                tasks.append(_task(5, "flag_missing_po", "Executor", ["T1"], "No valid PO reference: 3-way match impossible"))
            n = len(tasks)
            deps = [t["id"] for t in tasks[1:]]
        else:
            n, deps = 1, ["T1"]
        tasks += [
            _task(n + 1, "apply_policy_decision", "Resolution", deps, "Rule-based decision from findings + policy"),
            _task(n + 2, "independent_validation", "Critic", [f"T{n + 1}"], "Critic re-derives everything from raw data"),
            _task(n + 3, "route_for_review", "Orchestrator", [f"T{n + 2}"], "Auto-approve only if clean, else human queue"),
        ]
        return tasks


# =============================================================== 2. Research
def _tok(s: str) -> list[str]:
    return re.findall(r"[a-z0-9\-]+", s.lower())


class ResearchAgent:
    """Fetches records (evidence) and retrieves policy clauses (keyword/IDF retrieval)."""
    name = "Research"

    def gather(self, inv: dict, dataset: dict) -> dict:
        vid, po_id = inv.get("vendor_id"), inv.get("po_id")
        return {
            "vendor": dataset["vendors"].get(vid),
            "po": dataset["pos"].get(po_id) if po_id else None,
            "grn": dataset["grns"].get(po_id) if po_id else None,
            "history": [h for h in dataset["history"] if h["vendor_id"] == vid],
        }

    def retrieve(self, query: str, policy: dict, k: int = 1) -> list[dict]:
        docs = [(c, set(_tok(c["title"] + " " + c["text"] + " " + " ".join(c["tags"])))) for c in policy["clauses"]]
        n = len(docs)
        df: dict[str, int] = {}
        for _, ts in docs:
            for t in ts:
                df[t] = df.get(t, 0) + 1
        q = set(_tok(query))
        scored = []
        for c, ts in docs:
            score = sum(math.log(1 + n / df[t]) for t in q & ts)
            scored.append((score, c))
        scored.sort(key=lambda x: -x[0])
        return [{"clause_id": c["id"], "title": c["title"], "score": round(s, 3)} for s, c in scored[:k] if s > 0]

    def cite(self, reasons: list[str], policy: dict) -> dict:
        out = {}
        for r in reasons:
            hit = self.retrieve(FINDING_QUERY[r], policy)
            if hit:
                out[r] = hit[0]
        return out


# =============================================================== 3. Executor
class ExecutorAgent:
    """Runs the deterministic tools named in the plan and records every call."""
    name = "Executor"

    def run(self, state, policy: dict) -> dict:
        inv, ev, p = state.invoice, state.evidence, policy["params"]
        res: dict = {"findings": []}
        findings: list[str] = []

        def call(tool, args, result):
            state.tool_calls.append({"attempt": state.attempts, "tool": tool, "args": args, "result": result})
            return result

        for task in [t for t in state.plan if t["owner"] == "Executor"]:
            name = task["task"]
            if name == "validate_input":
                res["validation"] = call(name, "invoice", T.validate_input(inv, p))
                if not res["validation"]["valid"]:
                    findings.append("INPUT_INVALID")
                else:
                    res["invoice_total"] = str(T.invoice_total(inv))
            elif name == "duplicate_check":
                res["duplicate"] = call(name, "invoice, vendor history", T.duplicate_check(inv, ev["history"], p["duplicate_window_days"]))
                if res["duplicate"]["is_duplicate"]:
                    findings.append("DUPLICATE_INVOICE")
            elif name == "bank_check":
                res["bank"] = call(name, "invoice, vendor master", T.bank_check(inv, ev["vendor"]))
                if res["bank"]["mismatch"]:
                    findings.append("BANK_MISMATCH")
            elif name == "tax_check":
                res["tax"] = call(name, "invoice, vendor master", T.tax_check(inv, ev["vendor"], p))
                if res["tax"]["mismatch"]:
                    findings.append("TAX_RATE_MISMATCH")
            elif name == "three_way_match":
                res["match"] = call(name, "invoice, PO, GRN", T.three_way_match(inv, ev["po"], ev["grn"], p))
                findings += res["match"]["findings"]
            elif name == "flag_missing_po":
                res["match"] = call(name, "invoice.po_id", {"po_found": False, "grn_found": False, "lines": [], "findings": ["NO_PO"]})
                findings.append("NO_PO")
            task["status"] = "done"
        res["findings"] = sorted(set(findings), key=list(FINDING_QUERY).index)
        if "invoice_total" in res and res.get("match", {}).get("lines"):
            partial = "QTY_OVER_RECEIVED" in findings
            res["prospective_payable"] = str(T.payable_amount(inv, res["match"], partial))
        else:
            res["prospective_payable"] = res.get("invoice_total", "0.00")
        return res


# =============================================================== 4. Resolution
class ResolutionAgent:
    """Specialised domain agent: turns findings into one policy decision (rule-based)."""
    name = "Resolution"

    def decide(self, state, policy: dict) -> dict:
        res, p = state.results, policy["params"]
        f = set(res["findings"])
        reasons = list(res["findings"])
        decision = next((d for code, d in DECISION_BY_FINDING.items() if code in f), None)
        if decision is None:
            prospective = T.D(res["prospective_payable"])
            if prospective > T.D(p["approval_limit_inr"]):
                decision = "ESCALATE"
                reasons.append("OVER_APPROVAL_LIMIT")
            elif "QTY_OVER_RECEIVED" in f:
                decision = "PAY_PARTIAL"
            else:
                decision = "APPROVE"
        total = T.D(res.get("invoice_total", "0"))
        payable = T.D(res["prospective_payable"]) if decision in ("APPROVE", "PAY_PARTIAL") else Decimal(0)
        return {"decision": decision, "reasons": reasons, "payable": str(T.money(payable)),
                "not_paid": str(T.money(total - payable)), "clauses": {}}


# =============================================================== 5. Critic
class CriticAgent:
    """Independent validator: re-derives findings, decision and amounts from RAW data using a
    different arithmetic path (exact fractions) and shares nothing with Executor/Resolution except
    the policy parameters."""
    name = "Critic"

    @staticmethod
    def _frac(x) -> Fraction:
        return Fraction(str(x))

    def _cents(self, fr: Fraction) -> int:
        return math.floor(fr * 100 + Fraction(1, 2))

    def _total(self, inv) -> Fraction:
        sub = sum((self._frac(l["qty"]) * self._frac(l["unit_price"]) for l in inv["lines"]), Fraction(0))
        return sub * (1 + self._frac(inv["tax_rate"]))

    def derive(self, inv: dict, ds: dict, params: dict) -> dict:
        norm = lambda s: "".join(ch for ch in str(s or "").upper() if ch.isalnum())
        found: set[str] = set()
        # --- completeness (own implementation)
        bad = False
        try:
            from datetime import date
            date.fromisoformat(str(inv.get("invoice_date")))
            bad |= not str(inv.get("invoice_no") or "").strip() or not inv.get("vendor_id") or not inv.get("lines")
            bad |= any(self._frac(l["qty"]) <= 0 or self._frac(l["unit_price"]) < 0 for l in inv.get("lines") or [])
            bad |= not (0 <= self._frac(inv.get("tax_rate")) <= Fraction(1, 2))
            if not bad:
                bad |= abs(self._cents(self._total(inv)) - self._cents(self._frac(inv["declared_total"]))) > 1
        except Exception:
            bad = True
        if bad:
            return {"findings": {"INPUT_INVALID"}, "decision": "HOLD", "payable_cents": 0}
        vendor = ds["vendors"].get(inv["vendor_id"])
        d0 = date.fromisoformat(inv["invoice_date"])
        tot_c = self._cents(self._total(inv))
        for h in ds["history"]:
            if h["vendor_id"] != inv["vendor_id"]:
                continue
            dd = abs((date.fromisoformat(h["invoice_date"]) - d0).days)
            if dd <= params["duplicate_window_days"] and norm(h["invoice_no"]) == norm(inv["invoice_no"]):
                found.add("DUPLICATE_INVOICE")
            if dd == 0 and self._cents(self._frac(h["total"])) == tot_c:
                found.add("DUPLICATE_INVOICE")
        if vendor and inv.get("bank_account") != vendor["bank_account"]:
            found.add("BANK_MISMATCH")
        want = self._frac(params["gst_rate_registered"] if vendor and vendor["gst_registered"] else params["gst_rate_unregistered"])
        if self._frac(inv["tax_rate"]) != want:
            found.add("TAX_RATE_MISMATCH")
        po = ds["pos"].get(inv.get("po_id")) if inv.get("po_id") else None
        partial_cents = None
        if po is None:
            found.add("NO_PO")
        else:
            grn = ds["grns"].get(po["po_id"])
            recv = {x["sku"]: self._frac(x["qty_received"]) for x in (grn or {}).get("lines", [])}
            if not recv:
                found.add("NO_GRN")
            ppx = {x["sku"]: self._frac(x["unit_price"]) for x in po["lines"]}
            tol = self._frac(params["price_tolerance_pct"]) / 100
            paid_sub, over = Fraction(0), False
            for l in inv["lines"]:
                q, px = self._frac(l["qty"]), self._frac(l["unit_price"])
                if l["sku"] not in ppx:
                    found.add("SKU_NOT_ON_PO")
                    continue
                if px > ppx[l["sku"]] * (1 + tol):
                    found.add("PRICE_OVER_TOLERANCE")
                if recv and q > recv.get(l["sku"], Fraction(0)) + self._frac(params["qty_over_tolerance"]):
                    found.add("QTY_OVER_RECEIVED")
                    over = True
                paid_sub += min(q, recv.get(l["sku"], Fraction(0))) * px
            if over:
                partial_cents = self._cents(paid_sub * (1 + self._frac(inv["tax_rate"])))
        decision = next((d for c, d in DECISION_BY_FINDING.items() if c in found), None)
        prospective = partial_cents if partial_cents is not None else tot_c
        if decision is None:
            if prospective > params["approval_limit_inr"] * 100:
                decision = "ESCALATE"
            elif partial_cents is not None:
                decision = "PAY_PARTIAL"
            else:
                decision = "APPROVE"
        pay = prospective if decision in ("APPROVE", "PAY_PARTIAL") else 0
        return {"findings": found, "decision": decision, "payable_cents": pay, "invoice_cents": tot_c}

    def review(self, state, policy: dict, dataset: dict) -> dict:
        inv, dec, res = state.invoice, state.decision, state.results
        exp = self.derive(inv, dataset, policy["params"])
        checks = []

        def add(cid, name, ok, detail):
            checks.append({"id": cid, "check": name, "passed": bool(ok), "detail": detail})

        valid = "INPUT_INVALID" not in exp["findings"]
        if valid:
            reported = round(float(res.get("invoice_total", "nan")) * 100) if res.get("invoice_total") else None
            add("K1", "Invoice total recomputed (exact fractions)", reported == exp["invoice_cents"],
                f"executor={res.get('invoice_total')} critic={exp['invoice_cents'] / 100:.2f}")
        else:
            add("K1", "Invoice total recomputed (exact fractions)", True, "skipped: invoice failed completeness checks")
        add("K2", "Findings match independent re-derivation", set(res["findings"]) == exp["findings"],
            f"executor={sorted(res['findings'])} critic={sorted(exp['findings'])}")
        add("K3", "Decision matches policy priority on independent findings", dec["decision"] == exp["decision"],
            f"agent={dec['decision']} critic={exp['decision']}")
        got = round(float(dec["payable"]) * 100)
        add("K4", "Payable amount matches independent recomputation", abs(got - exp["payable_cents"]) <= 1,
            f"agent={got / 100:.2f} critic={exp['payable_cents'] / 100:.2f}")
        safe = (dec["decision"] in ("APPROVE", "PAY_PARTIAL") or got == 0) and \
               (not valid or got <= exp["invoice_cents"])
        add("K5", "Payment safety (no payment on blocked decisions, never above invoice total)", safe,
            f"decision={dec['decision']} payable={got / 100:.2f}")
        hard = True
        if "BANK_MISMATCH" in exp["findings"] and dec["decision"] != "ESCALATE":
            hard = False
        if "DUPLICATE_INVOICE" in exp["findings"] and dec["decision"] in ("APPROVE", "PAY_PARTIAL"):
            hard = False
        add("K6", "Hard controls (bank change => escalate; duplicate => never paid)", hard, "evaluated on critic's own findings")
        known = {c["id"] for c in policy["clauses"]}
        cited = dec.get("clauses", {})
        ok7 = all(r in cited and cited[r]["clause_id"] in known for r in dec["reasons"])
        add("K7", "Every reason is backed by an existing policy clause", ok7, f"reasons={dec['reasons']}")
        names = {t["task"] for t in state.plan}
        need = {"duplicate_check", "bank_check", "tax_check"} if valid else {"validate_input"}
        if valid:
            need.add("three_way_match" if inv.get("po_id") in dataset["pos"] else "flag_missing_po")
        add("K8", "Plan did not skip mandatory controls", need <= names and all(
            t["status"] == "done" for t in state.plan if t["owner"] == "Executor"), f"missing={sorted(need - names)}")
        return {"passed": all(c["passed"] for c in checks), "checks": checks}

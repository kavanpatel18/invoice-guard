"""Deterministic business tools. All money maths uses Decimal; no LLM is involved here."""
from __future__ import annotations

import json
import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path


def D(x) -> Decimal:
    return Decimal(str(x))


def money(x) -> Decimal:
    return D(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def load_policy(path: str | Path | None = None) -> dict:
    p = Path(path) if path else Path(__file__).with_name("policy.json")
    return json.loads(p.read_text(encoding="utf-8"))


def normalize_invoice_no(s) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(s or "").upper())


def invoice_subtotal(inv: dict) -> Decimal:
    return sum((D(l["qty"]) * D(l["unit_price"]) for l in inv["lines"]), Decimal(0))


def invoice_total(inv: dict) -> Decimal:
    return money(invoice_subtotal(inv) * (1 + D(inv["tax_rate"])))


# --------------------------------------------------------------------------- tools
def validate_input(inv: dict, params: dict | None = None) -> dict:
    """Completeness + arithmetic validation of the invoice document."""
    tol = D((params or {}).get("amount_tolerance", 0.01))
    errors: list[str] = []
    if not str(inv.get("invoice_no") or "").strip():
        errors.append("MISSING_INVOICE_NO")
    if not inv.get("vendor_id"):
        errors.append("MISSING_VENDOR")
    try:
        date.fromisoformat(str(inv.get("invoice_date")))
    except ValueError:
        errors.append("BAD_DATE")
    lines = inv.get("lines") or []
    if not lines:
        errors.append("NO_LINES")
    for i, l in enumerate(lines, 1):
        try:
            if D(l["qty"]) <= 0:
                errors.append(f"LINE{i}_QTY_NOT_POSITIVE")
            if D(l["unit_price"]) < 0:
                errors.append(f"LINE{i}_NEGATIVE_PRICE")
        except Exception:
            errors.append(f"LINE{i}_NOT_NUMERIC")
    try:
        if not (0 <= D(inv.get("tax_rate")) <= Decimal("0.5")):
            errors.append("TAX_RATE_OUT_OF_RANGE")
    except Exception:
        errors.append("TAX_RATE_INVALID")
    if not errors:
        try:
            if abs(invoice_total(inv) - money(inv["declared_total"])) > tol:
                errors.append("TOTAL_MISMATCH")
        except Exception:
            errors.append("DECLARED_TOTAL_INVALID")
    return {"valid": not errors, "errors": errors}


def duplicate_check(inv: dict, history: list[dict], window_days: int) -> dict:
    n = normalize_invoice_no(inv["invoice_no"])
    d = date.fromisoformat(inv["invoice_date"])
    total = invoice_total(inv)
    for h in history:
        if h["vendor_id"] != inv["vendor_id"]:
            continue
        hd = date.fromisoformat(h["invoice_date"])
        if abs((d - hd).days) > window_days:
            continue
        if normalize_invoice_no(h["invoice_no"]) == n:
            return {"is_duplicate": True, "basis": "same vendor + invoice number", "matched": h}
        if money(h["total"]) == total and hd == d:
            return {"is_duplicate": True, "basis": "same vendor + amount + date", "matched": h}
    return {"is_duplicate": False, "basis": None, "matched": None}


def bank_check(inv: dict, vendor: dict | None) -> dict:
    master = vendor["bank_account"] if vendor else None
    return {"mismatch": vendor is not None and inv.get("bank_account") != master,
            "invoice_account": inv.get("bank_account"), "master_account": master}


def tax_check(inv: dict, vendor: dict | None, params: dict) -> dict:
    registered = bool(vendor and vendor["gst_registered"])
    expected = D(params["gst_rate_registered"] if registered else params["gst_rate_unregistered"])
    return {"expected_rate": float(expected), "invoice_rate": float(D(inv["tax_rate"])),
            "gst_registered": registered, "mismatch": D(inv["tax_rate"]) != expected}


def three_way_match(inv: dict, po: dict | None, grn: dict | None, params: dict) -> dict:
    """Match invoice lines to PO lines and goods-receipt lines."""
    tol = D(params["price_tolerance_pct"])
    qty_tol = D(params["qty_over_tolerance"])
    findings: list[str] = []
    if po is None:
        return {"po_found": False, "grn_found": False, "lines": [], "findings": ["NO_PO"]}
    po_lines = {l["sku"]: l for l in po["lines"]}
    recv = {l["sku"]: D(l["qty_received"]) for l in (grn or {}).get("lines", [])}
    grn_found = bool(recv)
    if not grn_found:
        findings.append("NO_GRN")
    out = []
    for l in inv["lines"]:
        pl = po_lines.get(l["sku"])
        if pl is None:
            findings.append("SKU_NOT_ON_PO")
            out.append({"sku": l["sku"], "inv_qty": float(D(l["qty"])), "po_qty": None, "recv_qty": 0.0,
                        "inv_price": float(D(l["unit_price"])), "po_price": None, "price_var_pct": None,
                        "price_ok": False, "qty_ok": False})
            continue
        var = (D(l["unit_price"]) - D(pl["unit_price"])) / D(pl["unit_price"]) * 100
        r = recv.get(l["sku"], Decimal(0))
        price_ok = var <= tol
        qty_ok = D(l["qty"]) <= r + qty_tol
        if not price_ok:
            findings.append("PRICE_OVER_TOLERANCE")
        if grn_found and not qty_ok:
            findings.append("QTY_OVER_RECEIVED")
        out.append({"sku": l["sku"], "inv_qty": float(D(l["qty"])), "po_qty": float(D(pl["qty"])),
                    "recv_qty": float(r), "inv_price": float(D(l["unit_price"])),
                    "po_price": float(D(pl["unit_price"])), "price_var_pct": round(float(var), 3),
                    "price_ok": price_ok, "qty_ok": qty_ok})
    return {"po_found": True, "grn_found": grn_found, "lines": out, "findings": sorted(set(findings))}


def payable_amount(inv: dict, match: dict, partial: bool) -> Decimal:
    """Full invoice total, or only the goods-receipted quantity (partial) incl. tax."""
    if not partial:
        return invoice_total(inv)
    sub = Decimal(0)
    for l, m in zip(inv["lines"], match["lines"]):
        sub += min(D(l["qty"]), D(m["recv_qty"])) * D(l["unit_price"])
    return money(sub * (1 + D(inv["tax_rate"])))

"""Baseline: naive 2-way match used in many simple AP rules. Same data, same tolerance."""
from __future__ import annotations

from . import tools as T


def baseline_decision(inv: dict, ds: dict, tol_pct: float = 2.0) -> str:
    po = ds["pos"].get(inv.get("po_id")) if inv.get("po_id") else None
    if po is None:
        return "MANUAL"
    po_sub = sum(T.D(l["qty"]) * T.D(l["unit_price"]) for l in po["lines"])
    try:
        inv_sub = T.invoice_subtotal(inv)
    except Exception:
        return "MANUAL"
    return "APPROVE" if inv_sub <= po_sub * (1 + T.D(tol_pct) / 100) else "MANUAL"

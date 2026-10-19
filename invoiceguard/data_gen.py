"""Reproducible SYNTHETIC dataset generator (vendors, POs, goods receipts, invoice history, invoices).

Every invoice is generated with a known anomaly and a ground-truth expected decision that is
written by the generator itself (never by the agents), so accuracy can be measured honestly.
"""
from __future__ import annotations

import json
import random
import sys
from datetime import date, timedelta
from decimal import Decimal

from .tools import D, invoice_total, money

CATALOG = {  # sku: (description, unit price INR, qty min, qty max)
    "SKU-PAPER": ("A4 paper ream", 320, 50, 400),
    "SKU-TONER": ("Toner cartridge", 4200, 5, 40),
    "SKU-CHAIR": ("Ergonomic chair", 9800, 2, 15),
    "SKU-LAPTOP": ("Laptop 14in", 58000, 1, 4),
    "SKU-SWITCH": ("24-port network switch", 21500, 1, 5),
    "SKU-LICENSE": ("Software licence (annual)", 12500, 5, 30),
    "SKU-RACK": ("Server rack", 185000, 3, 3),
}
VENDORS = [
    {"vendor_id": "V001", "name": "Aarav Office Supplies", "prefix": "AOS", "gst_registered": True},
    {"vendor_id": "V002", "name": "Bluepeak IT Distribution", "prefix": "BIT", "gst_registered": True},
    {"vendor_id": "V003", "name": "Cedar Furnishings", "prefix": "CED", "gst_registered": True},
    {"vendor_id": "V004", "name": "Dhruv Networks", "prefix": "DNW", "gst_registered": True},
    {"vendor_id": "V005", "name": "Evergreen Software Resale", "prefix": "EVG", "gst_registered": True},
    {"vendor_id": "V006", "name": "Fathom Hardware", "prefix": "FTH", "gst_registered": True},
    {"vendor_id": "V007", "name": "Gulmohar Stationers (unregistered)", "prefix": "GUL", "gst_registered": False},
    {"vendor_id": "V008", "name": "Horizon Datacentre Gear", "prefix": "HDG", "gst_registered": True},
]
PLAN = {"CLEAN": 18, "PRICE_TOL": 5, "PRICE_OVER": 5, "QTY_OVER": 6, "NO_GRN": 4, "DUPLICATE": 5,
        "BANK_CHANGE": 4, "TAX_MISMATCH": 4, "NO_PO": 4, "HIGH_VALUE": 3, "ARITH_ERROR": 2,
        "MULTI_BANK_QTY": 2, "MULTI_DUP_PRICE": 1}
EXPECTED = {"CLEAN": "APPROVE", "PRICE_TOL": "APPROVE", "PRICE_OVER": "HOLD", "QTY_OVER": "PAY_PARTIAL",
            "NO_GRN": "HOLD", "DUPLICATE": "REJECT", "BANK_CHANGE": "ESCALATE", "TAX_MISMATCH": "HOLD",
            "NO_PO": "HOLD", "HIGH_VALUE": "ESCALATE", "ARITH_ERROR": "HOLD",
            "MULTI_BANK_QTY": "ESCALATE", "MULTI_DUP_PRICE": "REJECT"}
LABELS = {"CLEAN": "Clean 3-way match", "PRICE_TOL": "Price +1% (within tolerance)",
          "PRICE_OVER": "Price above tolerance", "QTY_OVER": "Billed more than received",
          "NO_GRN": "No goods receipt yet", "DUPLICATE": "Duplicate invoice (re-formatted number)",
          "BANK_CHANGE": "Bank account changed", "TAX_MISMATCH": "Wrong GST rate",
          "NO_PO": "No purchase order", "HIGH_VALUE": "Clean but above approval limit",
          "ARITH_ERROR": "Declared total is wrong", "MULTI_BANK_QTY": "Bank change AND over-billing",
          "MULTI_DUP_PRICE": "Duplicate AND price over tolerance"}


def _po_lines(rng: random.Random, kind: str) -> list[dict]:
    if kind == "HIGH_VALUE":
        d, p, lo, hi = CATALOG["SKU-RACK"]
        return [{"sku": "SKU-RACK", "desc": d, "qty": rng.randint(lo, hi), "unit_price": p}]
    needs_qty = kind in ("QTY_OVER", "MULTI_BANK_QTY")
    while True:
        skus = rng.sample([s for s in CATALOG if s != "SKU-RACK"], rng.randint(1, 3))
        lines = [{"sku": s, "desc": CATALOG[s][0], "qty": rng.randint(CATALOG[s][2], CATALOG[s][3]),
                  "unit_price": CATALOG[s][1]} for s in skus]
        total = sum(l["qty"] * l["unit_price"] for l in lines) * 1.18
        if total < 400000 and (not needs_qty or any(l["qty"] >= 4 for l in lines)):
            return lines


def _make_case(ds: dict, rng: random.Random, i: int, kind: str) -> None:
    vendor = rng.choice(list(ds["vendors"].values()))
    tax = 0.18 if vendor["gst_registered"] else 0.0
    po_id = f"PO-{1000 + i}"
    po_date = date(2026, 8, 1) + timedelta(days=rng.randint(0, 20))
    lines = _po_lines(rng, kind)
    po = {"po_id": po_id, "vendor_id": vendor["vendor_id"], "po_date": po_date.isoformat(),
          "lines": [dict(l) for l in lines]}
    inv_lines = [{"sku": l["sku"], "qty": l["qty"], "unit_price": l["unit_price"]} for l in lines]
    recv = {l["sku"]: l["qty"] for l in lines}
    bank = vendor["bank_account"]
    inv_no = f"{vendor['prefix']}-{rng.randint(10000, 99999)}"
    inv_date = po_date + timedelta(days=rng.randint(10, 30))
    has_grn, declared_factor = True, 1.0

    if kind == "PRICE_TOL":
        inv_lines[0]["unit_price"] = round(inv_lines[0]["unit_price"] * 1.01, 2)
    if kind in ("PRICE_OVER", "MULTI_DUP_PRICE"):
        inv_lines[0]["unit_price"] = round(inv_lines[0]["unit_price"] * rng.uniform(1.08, 1.15), 2)
    if kind in ("QTY_OVER", "MULTI_BANK_QTY"):
        over_idx = next(k for k, l in enumerate(lines) if l["qty"] >= 4)
        l = lines[over_idx]
        recv[l["sku"]] = l["qty"] - rng.randint(1, l["qty"] // 2)
    if kind == "NO_GRN":
        has_grn = False
    if kind in ("BANK_CHANGE", "MULTI_BANK_QTY"):
        bank = f"SYN-{rng.randint(100000, 999999)}"
    if kind == "TAX_MISMATCH":
        tax = rng.choice([0.12, 0.05]) if vendor["gst_registered"] else 0.18
    if kind == "NO_PO":
        po_id = None
    if kind == "ARITH_ERROR":
        declared_factor = 1.05

    inv = {"invoice_id": f"INV-{i:03d}", "invoice_no": inv_no, "vendor_id": vendor["vendor_id"],
           "po_id": po_id, "invoice_date": inv_date.isoformat(), "lines": inv_lines,
           "tax_rate": tax, "bank_account": bank}
    inv["declared_total"] = float(money(invoice_total(inv) * D(declared_factor)))

    if po_id:
        ds["pos"][po_id] = po
        if has_grn:
            ds["grns"][po_id] = {"grn_id": f"GRN-{1000 + i}", "po_id": po_id,
                                 "lines": [{"sku": s, "qty_received": q} for s, q in recv.items()]}
    if kind in ("DUPLICATE", "MULTI_DUP_PRICE"):
        old_no = inv_no.lower().replace("-", " ")  # same number, different formatting
        ds["history"].append({"invoice_id": f"HIST-{i:03d}", "vendor_id": vendor["vendor_id"],
                              "invoice_no": old_no,
                              "invoice_date": (inv_date - timedelta(days=rng.randint(5, 40))).isoformat(),
                              "total": inv["declared_total"], "status": "PAID (synthetic)"})

    exp = EXPECTED[kind]
    if exp == "APPROVE":
        pay = Decimal(str(inv["declared_total"]))
    elif exp == "PAY_PARTIAL":
        sub = sum(min(D(l["qty"]), D(recv[l["sku"]])) * D(l["unit_price"]) for l in inv_lines)
        pay = money(sub * (1 + D(tax)))
    else:
        pay = Decimal(0)
    ds["invoices"].append(inv)
    ds["ground_truth"][inv["invoice_id"]] = {"anomaly": kind, "label": LABELS[kind],
                                              "expected_decision": exp, "expected_payable": float(pay)}


def generate_dataset(seed: int = 42) -> dict:
    rng = random.Random(seed)
    vendors = {}
    for v in VENDORS:
        vendors[v["vendor_id"]] = {**v, "bank_account": f"SYN-{rng.randint(100000, 999999)}",
                                   "payment_terms_days": rng.choice([15, 30, 45])}
    ds = {"meta": {"synthetic": True, "seed": seed, "note": "All records are synthetic; no real company data."},
          "vendors": vendors, "pos": {}, "grns": {}, "history": [], "invoices": [], "ground_truth": {}}
    kinds = [k for k, c in PLAN.items() for _ in range(c)]
    rng.shuffle(kinds)
    for i, kind in enumerate(kinds, 1):
        _make_case(ds, rng, i, kind)
    for j in range(15):  # unrelated historical invoices (filler for the duplicate search)
        v = rng.choice(list(vendors.values()))
        ds["history"].append({"invoice_id": f"HIST-F{j:02d}", "vendor_id": v["vendor_id"],
                              "invoice_no": f"{v['prefix']}-{rng.randint(1000, 9999)}",
                              "invoice_date": (date(2026, 7, 1) + timedelta(days=rng.randint(0, 40))).isoformat(),
                              "total": round(rng.uniform(2000, 90000), 2), "status": "PAID (synthetic)"})
    return ds


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    path = sys.argv[2] if len(sys.argv) > 2 else "data/synthetic_dataset.json"
    json.dump(generate_dataset(seed), open(path, "w"), indent=1)
    print(f"wrote {path} (seed={seed})")

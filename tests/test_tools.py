import copy
from decimal import Decimal
from conftest import first
from invoiceguard import tools as T


def test_money_rounding_half_up():
    assert T.money("10.005") == Decimal("10.01") and T.money(2.5) == Decimal("2.50")


def test_invoice_total_math():
    inv = {"lines": [{"qty": 3, "unit_price": 100.10}], "tax_rate": 0.18}
    assert T.invoice_total(inv) == Decimal("354.35")  # 300.30 * 1.18 = 354.354


def test_normalize_invoice_no():
    assert T.normalize_invoice_no(" aos-12 345 ") == "AOS12345"


def test_validate_missing_and_invalid(ds):
    inv = copy.deepcopy(first(ds, "CLEAN"))
    assert T.validate_input(inv)["valid"]
    for field, val, code in [("invoice_no", "", "MISSING_INVOICE_NO"), ("invoice_date", "31/13/2026", "BAD_DATE"),
                             ("lines", [], "NO_LINES"), ("tax_rate", 0.9, "TAX_RATE_OUT_OF_RANGE")]:
        bad = copy.deepcopy(inv); bad[field] = val
        assert code in T.validate_input(bad)["errors"], code
    bad = copy.deepcopy(inv); bad["lines"][0]["qty"] = -2
    assert "LINE1_QTY_NOT_POSITIVE" in T.validate_input(bad)["errors"]
    bad = copy.deepcopy(inv); bad["lines"][0]["qty"] = "abc"
    assert "LINE1_NOT_NUMERIC" in T.validate_input(bad)["errors"]
    bad = copy.deepcopy(inv); bad["declared_total"] += 500
    assert "TOTAL_MISMATCH" in T.validate_input(bad)["errors"]


def test_duplicate_detects_reformatted_number(ds, policy):
    inv = first(ds, "DUPLICATE")
    hist = [h for h in ds["history"] if h["vendor_id"] == inv["vendor_id"]]
    r = T.duplicate_check(inv, hist, 90)
    assert r["is_duplicate"] and r["basis"] == "same vendor + invoice number"
    assert not T.duplicate_check(first(ds, "CLEAN"), ds["history"], 90)["is_duplicate"]


def test_duplicate_window_edge(ds):
    inv = first(ds, "DUPLICATE")
    hist = [dict(h) for h in ds["history"] if h["vendor_id"] == inv["vendor_id"] and h["invoice_id"].startswith("HIST-0")]
    for h in hist:
        h["invoice_date"] = "2020-01-01"
    assert not T.duplicate_check(inv, hist, 90)["is_duplicate"]  # outside 90-day window


def test_bank_and_tax(ds, policy):
    inv = first(ds, "BANK_CHANGE"); v = ds["vendors"][inv["vendor_id"]]
    assert T.bank_check(inv, v)["mismatch"]
    assert not T.bank_check(first(ds, "CLEAN"), ds["vendors"][first(ds, "CLEAN")["vendor_id"]])["mismatch"]
    t = first(ds, "TAX_MISMATCH")
    assert T.tax_check(t, ds["vendors"][t["vendor_id"]], policy["params"])["mismatch"]


def test_price_tolerance_boundary(ds, policy):
    inv = copy.deepcopy(first(ds, "CLEAN")); po = ds["pos"][inv["po_id"]]; grn = ds["grns"][inv["po_id"]]
    base = po["lines"][0]["unit_price"]
    inv["lines"][0]["unit_price"] = base * 1.02          # exactly 2% -> allowed
    assert "PRICE_OVER_TOLERANCE" not in T.three_way_match(inv, po, grn, policy["params"])["findings"]
    inv["lines"][0]["unit_price"] = base * 1.0201        # just above
    assert "PRICE_OVER_TOLERANCE" in T.three_way_match(inv, po, grn, policy["params"])["findings"]


def test_qty_over_and_partial_payable(ds, policy):
    inv = first(ds, "QTY_OVER"); po, grn = ds["pos"][inv["po_id"]], ds["grns"][inv["po_id"]]
    m = T.three_way_match(inv, po, grn, policy["params"])
    assert "QTY_OVER_RECEIVED" in m["findings"]
    assert T.payable_amount(inv, m, True) < T.invoice_total(inv)
    assert float(T.payable_amount(inv, m, True)) == ds["ground_truth"][inv["invoice_id"]]["expected_payable"]


def test_no_po_no_grn_and_sku_not_on_po(ds, policy):
    assert T.three_way_match(first(ds, "NO_PO"), None, None, policy["params"])["findings"] == ["NO_PO"]
    inv = first(ds, "NO_GRN"); m = T.three_way_match(inv, ds["pos"][inv["po_id"]], None, policy["params"])
    assert "NO_GRN" in m["findings"]
    inv2 = copy.deepcopy(first(ds, "CLEAN")); inv2["lines"][0]["sku"] = "SKU-UNKNOWN"
    assert "SKU_NOT_ON_PO" in T.three_way_match(inv2, ds["pos"][inv2["po_id"]], ds["grns"][inv2["po_id"]], policy["params"])["findings"]

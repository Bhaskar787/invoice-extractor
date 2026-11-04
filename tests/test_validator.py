"""
Unit Tests for Invoice Validator.

Tests all financial arithmetic, business rules, and edge cases
in src.validator without making any external API calls.
"""

from __future__ import annotations

import copy
import math
import pytest

from src.validator import validate_invoice


@pytest.fixture
def valid_invoice() -> dict:
    """Returns a valid dictionary representing the sample Rivertech invoice."""
    return {
        "invoice_number": "RT-2024-1052",
        "invoice_date": "2024-10-14",
        "supplier_name": "Rivertech Supplies Ltd.",
        "currency": "NPR",
        "items": [
            {
                "description": "HDPE Pipe 110mm (6m length)",
                "quantity": 50,
                "unit_price": 1250.0,
            },
            {
                "description": "HDPE Elbow 90 degree 110mm",
                "quantity": 20,
                "unit_price": 450.0,
            },
            {
                "description": "HDPE Coupling 110mm",
                "quantity": 30,
                "unit_price": 300.0,
            },
            {
                "description": "Welding Service",
                "quantity": 10,
                "unit_price": 1500.0,
            },
            {
                "description": "Delivery Charge",
                "quantity": 1,
                "unit_price": 5000.0,
            },
        ],
        "subtotal": 100500.0,
        "tax_amount": 13065.0,
        "total_amount": 113565.0,
    }


# ============================================================================
# Core Happy Path & Total Arithmetic
# ============================================================================

def test_correct_invoice_passes_validation(valid_invoice: dict) -> None:
    """Test 1: The standard correct invoice must pass all validation checks."""
    result = validate_invoice(valid_invoice)
    assert result["is_valid"] is True
    assert result["errors"] == []
    assert len(result["warnings"]) == 0
    assert result["calculated_details"]["calculated_items_sum"] == 100500.0
    assert len(result["calculated_details"]["item_line_totals"]) == 5


def test_wrong_total_amount_fails_with_clear_error(valid_invoice: dict) -> None:
    """Test 2: A mismatched total_amount must fail validation with a clear error."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["total_amount"] = 110000.0  # Incorrect total (expected 113565.0)

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert len(result["errors"]) > 0

    error_summary = " ".join(result["errors"])
    assert "does not match extracted total" in error_summary
    assert "113565.00" in error_summary
    assert "110000.00" in error_summary


def test_wrong_line_total_fails(valid_invoice: dict) -> None:
    """Test 3: If an item calculation causes item sum to mismatch subtotal, validation fails."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["items"][0]["quantity"] = 40  # Sum becomes 88,000 instead of 100,500

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert len(result["errors"]) > 0

    error_summary = " ".join(result["errors"])
    assert "Calculated items sum" in error_summary
    assert "does not match extracted subtotal" in error_summary


# ============================================================================
# Required Fields & Format Checks (Issues 35, 36, 4)
# ============================================================================

def test_missing_supplier_name(valid_invoice: dict) -> None:
    """Issue 35: Missing supplier_name must invalidate the invoice."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["supplier_name"] = None

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("Missing required field: 'supplier_name'" in err for err in result["errors"])


def test_missing_invoice_date(valid_invoice: dict) -> None:
    """Issue 36: Missing invoice_date must invalidate the invoice."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["invoice_date"] = None

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("Missing required field: 'invoice_date'" in err for err in result["errors"])


def test_missing_invoice_number(valid_invoice: dict) -> None:
    """Issue 4: Missing invoice_number is reported as an error without crashing."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["invoice_number"] = None

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("Missing required field: 'invoice_number'" in err for err in result["errors"])


def test_invalid_date_is_caught(valid_invoice: dict) -> None:
    """Test 5: An invalid or non-ISO date string is caught and flagged."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["invoice_date"] = "14/10/2024"

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("Invalid invoice_date format" in err for err in result["errors"])


def test_impossible_calendar_date_is_caught(valid_invoice: dict) -> None:
    """Calendar dates like Feb 31 must be rejected."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["invoice_date"] = "2024-02-31"

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("Invalid invoice_date format" in err for err in result["errors"])


# ============================================================================
# Line Items Constraints (Issues 37, 38, 39, 40, 41, 42, 43, 44)
# ============================================================================

def test_missing_item_description(valid_invoice: dict) -> None:
    """Issue 37: Missing or blank item description must fail validation."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["items"][0]["description"] = None

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("Description is missing or blank" in err for err in result["errors"])


def test_missing_quantity_fails_validation(valid_invoice: dict) -> None:
    """Issue 38 (Critical Issue 3): Missing quantity must be an ERROR, not a warning."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["items"][0]["quantity"] = None

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("Missing mandatory quantity" in err for err in result["errors"])


def test_missing_unit_price_fails_validation(valid_invoice: dict) -> None:
    """Issue 39 (Critical Issue 4): Missing unit price must be an ERROR, not a warning."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["items"][0]["unit_price"] = None

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("Missing mandatory unit price" in err for err in result["errors"])


def test_empty_items_array_is_rejected(valid_invoice: dict) -> None:
    """Issue 40: Empty items array must invalidate the invoice."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["items"] = []

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("must contain at least one line item" in err for err in result["errors"])


def test_items_supplied_as_string_is_rejected(valid_invoice: dict) -> None:
    """Issue 41 (Critical Issue 5): Items supplied as string must fail validation."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["items"] = "item 1, item 2"

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("must be a list of item objects" in err for err in result["errors"])


def test_invalid_item_object_is_detected(valid_invoice: dict) -> None:
    """Issue 42: Items containing non-dict objects must fail validation."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["items"].append("invalid string item")

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("expected an object" in err for err in result["errors"])


def test_negative_quantity_is_rejected(valid_invoice: dict) -> None:
    """Issue 43: Negative quantity must fail validation."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["items"][0]["quantity"] = -5

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("Quantity must be strictly greater than 0" in err for err in result["errors"])


def test_zero_quantity_is_rejected(valid_invoice: dict) -> None:
    """Zero quantity must fail validation."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["items"][0]["quantity"] = 0

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("Quantity must be strictly greater than 0" in err for err in result["errors"])


def test_negative_unit_price_is_rejected(valid_invoice: dict) -> None:
    """Issue 44: Negative unit price must fail validation."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["items"][0]["unit_price"] = -10.0

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("Unit price cannot be negative" in err for err in result["errors"])


# ============================================================================
# Non-Negative & Finite Monetary Checks (Issues 45, 46, 20, 21, 22)
# ============================================================================

def test_negative_total_amount_is_rejected(valid_invoice: dict) -> None:
    """Issue 45: Negative total_amount must fail validation."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["total_amount"] = -100.0

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("cannot be negative" in err for err in result["errors"])


def test_negative_subtotal_is_rejected(valid_invoice: dict) -> None:
    """Negative subtotal must fail validation."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["subtotal"] = -500.0

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("cannot be negative" in err for err in result["errors"])


def test_negative_tax_amount_is_rejected(valid_invoice: dict) -> None:
    """Negative tax_amount must fail validation."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["tax_amount"] = -50.0

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("cannot be negative" in err for err in result["errors"])


def test_nan_and_infinity_rejected(valid_invoice: dict) -> None:
    """Issue 46: NaN and Infinity must be rejected in all numeric fields."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["total_amount"] = float("nan")

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("must be a finite number" in err for err in result["errors"])

    invoice["total_amount"] = float("inf")
    result2 = validate_invoice(invoice)
    assert result2["is_valid"] is False
    assert any("must be a finite number" in err for err in result2["errors"])


def test_boolean_values_rejected_as_numbers(valid_invoice: dict) -> None:
    """Issue 10 & 20: Booleans (True/False) must not pass as numbers."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["items"][0]["quantity"] = True

    result = validate_invoice(invoice)
    assert result["is_valid"] is False
    assert any("must be a finite number" in err for err in result["errors"])


# ============================================================================
# Missing Optional Fields & Graceful Degradation (Issues 48, 49, 23, 24)
# ============================================================================

def test_missing_subtotal_generates_warning_not_crash(valid_invoice: dict) -> None:
    """Issue 48: Missing subtotal is warned, not a crash."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["subtotal"] = None

    result = validate_invoice(invoice)
    # The invoice calculations (items + tax == total) still match!
    assert result["is_valid"] is True
    assert any("Subtotal is not provided" in w for w in result["warnings"])


def test_missing_tax_with_matching_total(valid_invoice: dict) -> None:
    """Issue 49: Missing tax amount when total equals items sum passes as tax-exempt."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["tax_amount"] = None
    invoice["total_amount"] = 100500.0  # Equal to items sum

    result = validate_invoice(invoice)
    assert result["is_valid"] is True
    assert any("Tax amount is not provided" in w for w in result["warnings"])


def test_missing_tax_with_differing_total_warns(valid_invoice: dict) -> None:
    """Missing tax amount when total differs from items sum warns of unverified difference."""
    invoice = copy.deepcopy(valid_invoice)
    invoice["tax_amount"] = None
    invoice["total_amount"] = 113565.0  # Items sum is 100,500

    result = validate_invoice(invoice)
    assert any("cannot definitively verify without tax" in w for w in result["warnings"])

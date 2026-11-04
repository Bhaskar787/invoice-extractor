"""
Unit tests for src/utils.py.
"""

from decimal import Decimal
import json
import math
import pytest
import pandas as pd

from src.utils import (
    build_items_dataframe,
    calculate_item_line_total,
    format_currency,
    format_quantity,
    generate_export_payload,
    safe_decimal,
)


class TestSafeDecimal:
    """Tests for safe_decimal helper."""

    def test_valid_numbers_and_strings(self):
        assert safe_decimal(10) == Decimal("10")
        assert safe_decimal(10.5) == Decimal("10.5")
        assert safe_decimal("123.45") == Decimal("123.45")
        assert safe_decimal("  50  ") == Decimal("50")

    def test_booleans_rejected(self):
        assert safe_decimal(True) is None
        assert safe_decimal(False) is None

    def test_none_and_invalids(self):
        assert safe_decimal(None) is None
        assert safe_decimal("invalid") is None
        assert safe_decimal("") is None
        assert safe_decimal(float("nan")) is None
        assert safe_decimal(float("inf")) is None
        assert safe_decimal(float("-inf")) is None


class TestFormatCurrency:
    """Tests for format_currency."""

    def test_standard_formatting(self):
        assert format_currency(113565, "NPR") == "NPR 113,565.00"
        assert format_currency(1234.5, "USD") == "USD 1,234.50"
        assert format_currency(0, "EUR") == "EUR 0.00"

    def test_negative_values(self):
        assert format_currency(-50.5, "USD") == "-USD 50.50"

    def test_missing_or_invalid_values(self):
        assert format_currency(None) == "Not specified"
        assert format_currency(True) == "Not specified"
        assert format_currency(False) == "Not specified"
        assert format_currency(float("nan")) == "Not specified"
        assert format_currency(float("inf")) == "Not specified"
        assert format_currency("not_a_number") == "Not specified"

    def test_default_currency(self):
        assert format_currency(100) == "NPR 100.00"
        assert format_currency(100, None) == "NPR 100.00"


class TestFormatQuantity:
    """Tests for format_quantity."""

    def test_whole_numbers(self):
        assert format_quantity(50.0) == "50"
        assert format_quantity(1) == "1"
        assert format_quantity(1000) == "1000"

    def test_decimal_quantities(self):
        assert format_quantity(12.5) == "12.5"
        assert format_quantity(0.75) == "0.75"

    def test_missing_or_invalid(self):
        assert format_quantity(None) == "Missing"
        assert format_quantity(True) == "Missing"
        assert format_quantity(float("nan")) == "Missing"
        assert format_quantity(float("inf")) == "Missing"


class TestCalculateItemLineTotal:
    """Tests for calculate_item_line_total."""

    def test_valid_multiplication(self):
        assert calculate_item_line_total(2, 50.0) == 100.0
        assert calculate_item_line_total("3", "19.99") == 59.97
        assert calculate_item_line_total(1.5, 10.0) == 15.0

    def test_rounding(self):
        # 1.005 * 10 = 10.05
        assert calculate_item_line_total(1.005, 10) == 10.05

    def test_missing_and_zero_inputs(self):
        assert calculate_item_line_total(None, 10) is None
        assert calculate_item_line_total(5, None) is None
        assert calculate_item_line_total(0, 10) is None  # Quantity must be > 0
        assert calculate_item_line_total(-1, 10) is None
        assert calculate_item_line_total(5, -1) is None
        assert calculate_item_line_total(5, 0) == 0.0  # Unit price 0 is acceptable (free item)

    def test_boolean_rejection(self):
        assert calculate_item_line_total(True, 10) is None
        assert calculate_item_line_total(5, False) is None


class TestBuildItemsDataframe:
    """Tests for build_items_dataframe."""

    def test_empty_or_none(self):
        df_none = build_items_dataframe(None)
        assert isinstance(df_none, pd.DataFrame)
        assert list(df_none.columns) == ["#", "Description", "Quantity", "Unit Price", "Line Total"]
        assert len(df_none) == 0

        df_empty = build_items_dataframe([])
        assert len(df_empty) == 0

    def test_populated_items(self):
        items = [
            {"description": "Item 1", "quantity": 2, "unit_price": 50.0},
            {"description": "Item 2", "quantity": 1.5, "unit_price": 20.0},
        ]
        df = build_items_dataframe(items, currency="NPR")
        assert len(df) == 2
        assert df.iloc[0]["#"] == 1
        assert df.iloc[0]["Description"] == "Item 1"
        assert df.iloc[0]["Quantity"] == "2"
        assert df.iloc[0]["Unit Price"] == "NPR 50.00"
        assert df.iloc[0]["Line Total"] == "NPR 100.00"

    def test_corrupted_items(self):
        items = ["not_a_dict", None]
        df = build_items_dataframe(items)
        assert len(df) == 2
        assert "Corrupted" in df.iloc[0]["Description"]


class TestGenerateExportPayload:
    """Tests for generate_export_payload."""

    def test_valid_json_serialization(self):
        inv_data = {"invoice_number": "INV-001", "total_amount": 100.0}
        val_data = {"is_valid": True, "errors": []}
        json_str = generate_export_payload(inv_data, val_data)

        parsed = json.loads(json_str)
        assert "invoice_data" in parsed
        assert "validation" in parsed
        assert parsed["invoice_data"]["invoice_number"] == "INV-001"
        assert parsed["validation"]["is_valid"] is True

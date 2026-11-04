"""
Utilities Module.

Provides financial formatting, decimal rounding helpers, DataFrame table generators,
and JSON export payload serialization for InvoiceAI.
"""

from __future__ import annotations

import json
import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Union

import pandas as pd


def safe_decimal(val: Any) -> Optional[Decimal]:
    """
    Safely converts a numeric value or numeric string to Decimal.
    Explicitly rejects booleans, NaN, Infinity, None, and unparseable strings.
    """
    if isinstance(val, bool) or val is None:
        return None
    try:
        dec = Decimal(str(val).strip())
        if dec.is_nan() or dec.is_infinite():
            return None
        return dec
    except (InvalidOperation, TypeError, ValueError):
        return None


def format_currency(
    amount: Optional[Union[float, int, Decimal]],
    currency: Optional[str] = "NPR",
) -> str:
    """
    Formats a numeric amount with standard currency grouping and 2 decimal places.

    Examples:
        format_currency(113565, "NPR") -> "NPR 113,565.00"
        format_currency(None) -> "Not specified"
        format_currency(-50.5, "USD") -> "-USD 50.50"
    """
    if amount is None or isinstance(amount, bool):
        return "Not specified"

    curr_code = (currency or "NPR").strip()

    try:
        val = float(amount)
        if math.isnan(val) or math.isinf(val):
            return "Not specified"

        if val < 0:
            return f"-{curr_code} {abs(val):,.2f}"
        return f"{curr_code} {val:,.2f}"
    except (ValueError, TypeError):
        return "Not specified"


def format_quantity(qty: Optional[Union[float, int]]) -> str:
    """
    Formats item quantity cleanly, omitting trailing zeroes for whole numbers.

    Examples:
        format_quantity(50.0) -> "50"
        format_quantity(12.5) -> "12.5"
        format_quantity(None) -> "Missing"
    """
    if qty is None or isinstance(qty, bool):
        return "Missing"
    try:
        val = float(qty)
        if math.isnan(val) or math.isinf(val):
            return "Missing"
        return str(int(val)) if val.is_integer() else f"{val:g}"
    except (ValueError, TypeError):
        return "Missing"


def calculate_item_line_total(
    quantity: Any,
    unit_price: Any,
) -> Optional[float]:
    """
    Calculates line total (quantity * unit_price) using Decimal arithmetic
    with ROUND_HALF_UP and returns float rounded to 2 decimal places.
    """
    dec_qty = safe_decimal(quantity)
    dec_price = safe_decimal(unit_price)

    if dec_qty is None or dec_price is None:
        return None

    if dec_qty <= 0 or dec_price < 0:
        return None

    total = (dec_qty * dec_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(total)


def build_items_dataframe(
    items: Optional[List[Dict[str, Any]]],
    currency: str = "NPR",
) -> pd.DataFrame:
    """
    Transforms the line items list into a styled pandas DataFrame for Streamlit display.

    Columns:
        - "#": Row index (1-based)
        - "Description": Item name or service description
        - "Quantity": Formatted quantity
        - "Unit Price": Formatted unit price
        - "Line Total": Formatted line total
    """
    columns = ["#", "Description", "Quantity", "Unit Price", "Line Total"]

    if not items or not isinstance(items, list):
        return pd.DataFrame(columns=columns)

    curr_code = (currency or "NPR").strip()
    rows = []

    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            rows.append(
                {
                    "#": idx,
                    "Description": "[Corrupted / Invalid Item Object]",
                    "Quantity": "Invalid",
                    "Unit Price": "Invalid",
                    "Line Total": "Invalid",
                }
            )
            continue

        desc = item.get("description")
        desc_display = str(desc).strip() if desc is not None and str(desc).strip() else "[Description missing]"

        qty = item.get("quantity")
        price = item.get("unit_price")

        qty_str = format_quantity(qty)
        price_str = format_currency(price, curr_code) if price is not None else "[Price missing]"

        # Check if pre-calculated line total exists, or compute it
        computed = item.get("calculated_line_total")
        if computed is None:
            computed = calculate_item_line_total(qty, price)

        total_str = format_currency(computed, curr_code) if computed is not None else "[Discrepancy]"

        rows.append(
            {
                "#": idx,
                "Description": desc_display,
                "Quantity": qty_str,
                "Unit Price": price_str,
                "Line Total": total_str,
            }
        )

    return pd.DataFrame(rows)


def generate_export_payload(
    invoice_data: Dict[str, Any],
    validation: Dict[str, Any],
) -> str:
    """
    Serializes the complete unified invoice extraction and validation
    report into clean, indented JSON.
    """
    payload = {
        "invoice_data": invoice_data,
        "validation": validation,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)

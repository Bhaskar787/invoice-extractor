"""
Validator Module.

Validates extracted invoice data against financial arithmetic and business rules:
1. Presence and type validity of mandatory fields.
2. Line items structure (must be a non-empty list of valid objects).
3. Item constraints (non-empty description, quantity > 0, unit_price >= 0).
4. Finite numeric values (rejects NaN, Infinity, and Booleans).
5. Non-negative monetary amounts (subtotal, tax_amount, total_amount >= 0).
6. Independent line total calculations (quantity * unit_price).
7. Arithmetic consistency (items sum vs. subtotal, subtotal + tax vs. grand total).
8. Calendar date reality and ISO format compliance (YYYY-MM-DD).

Produces clear, actionable error and warning messages without crashing.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# Permissible delta between calculated and extracted currency values for rounding
FLOAT_TOLERANCE = 0.01

REQUIRED_FIELDS = [
    "invoice_number",
    "invoice_date",
    "supplier_name",
    "items",
    "total_amount",
]


def _is_finite_number(val: Any) -> bool:
    """Check if value is a valid, finite int or float (explicitly rejects bool)."""
    if isinstance(val, bool) or val is None:
        return False
    if not isinstance(val, (int, float)):
        return False
    return not (math.isnan(val) or math.isinf(val))


def _is_valid_date(date_str: Any) -> bool:
    """Check if a date string is in valid YYYY-MM-DD format and is a real calendar date."""
    if not isinstance(date_str, str) or not date_str.strip():
        return False
    try:
        parsed = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        # Ensure year is reasonable (e.g. 1900 to 2100)
        return 1900 <= parsed.year <= 2100
    except (ValueError, TypeError):
        return False


def validate_invoice(data: Any) -> Dict[str, Any]:
    """
    Validates extracted invoice data against financial and integrity rules.

    Args:
        data: Cleaned invoice data dictionary.

    Returns:
        dict containing:
            - is_valid (bool): True if zero errors were found, False otherwise.
            - errors (list[str]): Critical discrepancies or missing mandatory fields.
            - warnings (list[str]): Non-critical notifications or unperformed checks due to missing optional fields.
            - calculated_details (dict): Line-by-line computed amounts for auditability.
    """
    errors: List[str] = []
    warnings: List[str] = []
    item_line_totals: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------------
    # 0. Root Structure Check
    # ------------------------------------------------------------------------
    if not isinstance(data, dict):
        return {
            "is_valid": False,
            "errors": [f"Invoice data must be a dictionary, got {type(data).__name__}."],
            "warnings": [],
            "calculated_details": {"item_line_totals": [], "calculated_items_sum": None},
        }

    # ------------------------------------------------------------------------
    # 1. Required Top-Level Fields Check
    # ------------------------------------------------------------------------
    for field in REQUIRED_FIELDS:
        val = data.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"Missing required field: '{field}'.")

    # ------------------------------------------------------------------------
    # 2. Invoice Date Format Check
    # ------------------------------------------------------------------------
    invoice_date = data.get("invoice_date")
    if invoice_date is not None:
        if not _is_valid_date(invoice_date):
            errors.append(
                f"Invalid invoice_date format '{invoice_date}': expected YYYY-MM-DD (valid calendar date)."
            )

    # ------------------------------------------------------------------------
    # 3. Monetary Summary Fields Validation (Total, Subtotal, Tax)
    # ------------------------------------------------------------------------
    total_amount = data.get("total_amount")
    if total_amount is not None:
        if not _is_finite_number(total_amount):
            errors.append(
                f"Field 'total_amount' must be a finite number, got {type(total_amount).__name__} ({total_amount})."
            )
        elif total_amount < 0:
            errors.append(f"Field 'total_amount' cannot be negative, got {total_amount}.")

    subtotal = data.get("subtotal")
    if subtotal is not None:
        if not _is_finite_number(subtotal):
            errors.append(
                f"Field 'subtotal' must be a finite number, got {type(subtotal).__name__} ({subtotal})."
            )
        elif subtotal < 0:
            errors.append(f"Field 'subtotal' cannot be negative, got {subtotal}.")

    tax_amount = data.get("tax_amount")
    if tax_amount is not None:
        if not _is_finite_number(tax_amount):
            errors.append(
                f"Field 'tax_amount' must be a finite number, got {type(tax_amount).__name__} ({tax_amount})."
            )
        elif tax_amount < 0:
            errors.append(f"Field 'tax_amount' cannot be negative, got {tax_amount}.")

    # ------------------------------------------------------------------------
    # 4. Line Items Validation & Calculation
    # ------------------------------------------------------------------------
    items = data.get("items")
    calculated_items_total = 0.0
    all_items_computable = True

    if items is None:
        # Already handled by required field check
        all_items_computable = False
    elif not isinstance(items, list):
        errors.append(f"Field 'items' must be a list of item objects, got {type(items).__name__}.")
        all_items_computable = False
    elif len(items) == 0:
        errors.append("Invoice must contain at least one line item in 'items'.")
        all_items_computable = False
    else:
        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                errors.append(f"Item #{idx} is invalid: expected an object, got {type(item).__name__}.")
                all_items_computable = False
                continue

            desc = item.get("description")
            qty = item.get("quantity")
            price = item.get("unit_price")

            # Check description (Issue 2 & 13 & 37: must not be empty or placeholder)
            if desc is None or not str(desc).strip():
                errors.append(f"Item #{idx}: Description is missing or blank.")
                desc_label = f"Item #{idx}"
            else:
                desc_label = f"Item #{idx} ('{desc}')"

            item_computable = True

            # Check quantity (Issue 3 & 18: missing quantity is an ERROR, not warning)
            if qty is None:
                errors.append(f"{desc_label}: Missing mandatory quantity.")
                item_computable = False
            elif not _is_finite_number(qty):
                errors.append(
                    f"{desc_label}: Quantity must be a finite number, got {type(qty).__name__} ({qty})."
                )
                item_computable = False
            elif qty <= 0:
                errors.append(f"{desc_label}: Quantity must be strictly greater than 0, got {qty}.")
                item_computable = False

            # Check unit price (Issue 4 & 18: missing unit price is an ERROR, not warning)
            if price is None:
                errors.append(f"{desc_label}: Missing mandatory unit price.")
                item_computable = False
            elif not _is_finite_number(price):
                errors.append(
                    f"{desc_label}: Unit price must be a finite number, got {type(price).__name__} ({price})."
                )
                item_computable = False
            elif price < 0:
                errors.append(f"{desc_label}: Unit price cannot be negative, got {price}.")
                item_computable = False

            # If item is computable, calculate line total
            if item_computable:
                line_total = round(float(qty) * float(price), 2)
                calculated_items_total += line_total
                item_line_totals.append(
                    {
                        "item_index": idx,
                        "description": desc,
                        "quantity": qty,
                        "unit_price": price,
                        "calculated_line_total": line_total,
                    }
                )
            else:
                all_items_computable = False
                item_line_totals.append(
                    {
                        "item_index": idx,
                        "description": desc,
                        "quantity": qty,
                        "unit_price": price,
                        "calculated_line_total": None,
                    }
                )

    calculated_items_total = round(calculated_items_total, 2)

    # ------------------------------------------------------------------------
    # 5. Sum of Line Totals vs Subtotal
    # ------------------------------------------------------------------------
    if subtotal is not None and _is_finite_number(subtotal):
        if all_items_computable:
            if abs(calculated_items_total - float(subtotal)) > FLOAT_TOLERANCE:
                errors.append(
                    f"Calculated items sum {calculated_items_total:.2f} does not match extracted subtotal {float(subtotal):.2f}."
                )
        else:
            warnings.append(
                "Cannot verify extracted subtotal against items because one or more item calculations are incomplete."
            )
    elif subtotal is None:
        warnings.append(
            "Subtotal is not provided; skipping items sum vs. subtotal verification."
        )

    # ------------------------------------------------------------------------
    # 6. Subtotal + Tax Amount vs Total Amount
    # ------------------------------------------------------------------------
    if (
        subtotal is not None
        and _is_finite_number(subtotal)
        and tax_amount is not None
        and _is_finite_number(tax_amount)
        and total_amount is not None
        and _is_finite_number(total_amount)
    ):
        expected_total = round(float(subtotal) + float(tax_amount), 2)
        if abs(expected_total - float(total_amount)) > FLOAT_TOLERANCE:
            errors.append(
                f"Subtotal ({float(subtotal):.2f}) + tax ({float(tax_amount):.2f}) = {expected_total:.2f}, "
                f"which does not match extracted total ({float(total_amount):.2f})."
            )
    elif subtotal is not None and tax_amount is None:
        warnings.append(
            "Tax amount is not provided; skipping subtotal + tax = total verification."
        )

    # ------------------------------------------------------------------------
    # 7. Calculated Grand Total vs Extracted Total Amount
    # ------------------------------------------------------------------------
    if total_amount is not None and _is_finite_number(total_amount):
        if all_items_computable:
            if tax_amount is not None and _is_finite_number(tax_amount):
                expected_grand = round(calculated_items_total + float(tax_amount), 2)
                if abs(expected_grand - float(total_amount)) > FLOAT_TOLERANCE:
                    errors.append(
                        f"Calculated total {expected_grand:.2f} does not match extracted total {float(total_amount):.2f}."
                    )
            elif tax_amount is None:
                # If tax is not specified, check if items sum matches total amount directly (tax-exempt invoice)
                if abs(calculated_items_total - float(total_amount)) <= FLOAT_TOLERANCE:
                    # Items match total directly (no tax)
                    pass
                else:
                    warnings.append(
                        f"Tax amount is not provided. Items sum ({calculated_items_total:.2f}) differs from "
                        f"total amount ({float(total_amount):.2f}); cannot definitively verify without tax."
                    )
        else:
            warnings.append(
                "Cannot verify total amount against calculated items because item calculations are incomplete."
            )

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "calculated_details": {
            "calculated_items_sum": calculated_items_total if all_items_computable else None,
            "item_line_totals": item_line_totals,
        },
    }

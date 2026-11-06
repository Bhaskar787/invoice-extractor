"""
Validation Panel Component.

Renders:
1. Overall Validation Status Banner (Valid, Needs Review, Failed) using Bootstrap Icons.
2. Granular checks status breakdown (Mandatory Fields, Date Format, Line Items, Financial Arithmetic).
3. Explicit lists of errors and warnings with high-contrast, accessible typography.
4. Mathematical verification card displaying arithmetic balance with zero emojis.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import streamlit as st

from src.utils import format_currency


def render_validation_panel(
    validation_result: Optional[Dict[str, Any]],
    invoice_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Renders comprehensive validation results and financial calculation checks.

    Args:
        validation_result: Dictionary returned from validate_invoice().
        invoice_data: Optional dictionary containing extracted invoice fields.
    """
    if not validation_result:
        st.info("No validation results available yet.")
        return

    is_valid = validation_result.get("is_valid", False)
    errors: List[str] = validation_result.get("errors", [])
    warnings: List[str] = validation_result.get("warnings", [])
    calc_details = validation_result.get("calculated_details", {})

    currency = "NPR"
    if invoice_data:
        currency = invoice_data.get("currency") or "NPR"

    # 1. Overall status banner
    if is_valid and len(warnings) == 0:
        st.markdown(
            """
            <div style="background-color: #f0fdf4; border: 1.5px solid #86efac; border-radius: 10px; padding: 14px 18px; margin-bottom: 18px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <i class="bi bi-check-circle-fill" style="color: #16a34a; font-size: 1.6rem;"></i>
                    <div>
                        <h4 style="color: #14532d; margin: 0; font-weight: 700; font-size: 1.05rem;">
                            Invoice Status: Valid
                        </h4>
                        <p style="color: #15803d; margin: 2px 0 0 0; font-size: 0.84rem;">
                            All mandatory fields are present and all financial arithmetic checks passed with 100% precision.
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif is_valid and len(warnings) > 0:
        st.markdown(
            f"""
            <div style="background-color: #fffbeb; border: 1.5px solid #fde68a; border-radius: 10px; padding: 14px 18px; margin-bottom: 18px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <i class="bi bi-exclamation-triangle-fill" style="color: #d97706; font-size: 1.6rem;"></i>
                    <div>
                        <h4 style="color: #78350f; margin: 0; font-weight: 700; font-size: 1.05rem;">
                            Invoice Status: Needs Review ({len(warnings)} warning{'s' if len(warnings) > 1 else ''})
                        </h4>
                        <p style="color: #92400e; margin: 2px 0 0 0; font-size: 0.84rem;">
                            Invoice is logically acceptable, but optional fields or unverified calculations warrant attention.
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="background-color: #fef2f2; border: 1.5px solid #fca5a5; border-radius: 10px; padding: 14px 18px; margin-bottom: 18px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <i class="bi bi-x-circle-fill" style="color: #dc2626; font-size: 1.6rem;"></i>
                    <div>
                        <h4 style="color: #7f1d1d; margin: 0; font-weight: 700; font-size: 1.05rem;">
                            Invoice Status: Invalid ({len(errors)} error{'s' if len(errors) > 1 else ''})
                        </h4>
                        <p style="color: #991b1b; margin: 2px 0 0 0; font-size: 0.84rem;">
                            Critical validation errors found. Please correct the values in the Edit tab and click Validate Updated Invoice.
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Errors & warnings breakdown
    if errors:
        st.markdown(
            f"""
            <div style="color: #991b1b; font-weight: 700; font-size: 0.88rem; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                <i class="bi bi-x-octagon-fill" style="color: #dc2626;"></i>
                <span>Validation Errors ({len(errors)})</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for err in errors:
            st.markdown(
                f"""
                <div style="background-color: #fff1f2; border-left: 3px solid #e11d48; padding: 7px 12px; margin-bottom: 5px; border-radius: 0 6px 6px 0; color: #881337; font-size: 0.84rem; font-weight: 500;">
                    {err}
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    if warnings:
        st.markdown(
            f"""
            <div style="color: #92400e; font-weight: 700; font-size: 0.88rem; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                <i class="bi bi-exclamation-triangle-fill" style="color: #d97706;"></i>
                <span>Validation Warnings ({len(warnings)})</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for warn in warnings:
            st.markdown(
                f"""
                <div style="background-color: #fffbeb; border-left: 3px solid #f59e0b; padding: 7px 12px; margin-bottom: 5px; border-radius: 0 6px 6px 0; color: #78350f; font-size: 0.84rem; font-weight: 500;">
                    {warn}
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # 3. Granular rules audit grid
    st.markdown(
        """
        <div style="color: #0f172a; font-weight: 700; font-size: 0.92rem; margin-top: 10px; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
            <i class="bi bi-shield-check" style="color: #2563eb;"></i>
            <span>Granular Validation Audit</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Deduce check statuses from errors
    has_mandatory_err = any("Missing mandatory" in e or "Mandatory field" in e for e in errors)
    has_date_err = any("date" in e.lower() for e in errors)
    has_item_constraint_err = any("Quantity" in e or "Unit price" in e or "Description" in e for e in errors)
    has_subtotal_sum_err = any("Calculated items sum" in e and "subtotal" in e for e in errors)
    has_tax_total_err = any("Subtotal (" in e and "tax (" in e for e in errors)
    has_grand_total_err = any("Calculated total" in e and "extracted total" in e for e in errors)

    c1, c2, c3 = st.columns(3)

    def _render_check_card(title: str, passed: bool, pass_text: str, fail_text: str) -> str:
        color = "#166534" if passed else "#991b1b"
        bg = "#f0fdf4" if passed else "#fef2f2"
        border = "#bbf7d0" if passed else "#fecaca"
        icon = '<i class="bi bi-check-circle-fill" style="color: #16a34a;"></i>' if passed else '<i class="bi bi-x-circle-fill" style="color: #dc2626;"></i>'
        desc = pass_text if passed else fail_text
        return f"""
        <div style="background-color: {bg}; border: 1px solid {border}; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px;">
            <div style="font-weight: 700; font-size: 0.82rem; color: #0f172a; display: flex; align-items: center; gap: 6px;">
                {icon}
                <span>{title}</span>
            </div>
            <div style="font-size: 0.76rem; color: {color}; margin-top: 4px; font-weight: 500;">
                {desc}
            </div>
        </div>
        """

    with c1:
        st.markdown(
            _render_check_card(
                "Mandatory Fields",
                not has_mandatory_err,
                "All required fields detected",
                "Missing required header fields",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            _render_check_card(
                "Date Format",
                not has_date_err,
                "Valid ISO 8601 (YYYY-MM-DD)",
                "Invalid or unparseable date",
            ),
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            _render_check_card(
                "Item Constraints",
                not has_item_constraint_err,
                "Quantities > 0 and Prices >= 0",
                "Non-positive quantity or price",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            _render_check_card(
                "Items vs Subtotal",
                not has_subtotal_sum_err,
                "Sum(Items) = Subtotal",
                "Items sum mismatch",
            ),
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            _render_check_card(
                "Subtotal + Tax = Total",
                not has_tax_total_err,
                "Tax arithmetic holds",
                "Tax sum mismatch",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            _render_check_card(
                "Grand Total Match",
                not has_grand_total_err,
                "Independent total confirmed",
                "Discrepancy in grand total",
            ),
            unsafe_allow_html=True,
        )

    # 4. Arithmetic reconciliation summary
    if invoice_data:
        subtotal_val = invoice_data.get("subtotal")
        tax_val = invoice_data.get("tax_amount")
        total_val = invoice_data.get("total_amount")
        items_calc = calc_details.get("calculated_items_sum")

        with st.expander("View Detailed Financial Balance & Reconciliation", expanded=False):
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                st.metric("Reported Subtotal", format_currency(subtotal_val, currency))
            with rc2:
                st.metric("Sum of Line Items", format_currency(items_calc, currency))
            with rc3:
                st.metric("Reported Tax", format_currency(tax_val, currency))
            with rc4:
                st.metric("Reported Total", format_currency(total_val, currency))

            if subtotal_val is not None and items_calc is not None:
                diff = abs(float(subtotal_val) - float(items_calc))
                if diff <= 0.05:
                    st.caption("Items sum reconciles with reported subtotal within rounding tolerance (<= 0.05).")
                else:
                    st.caption(f"Subtotal difference: {currency} {diff:.2f}")

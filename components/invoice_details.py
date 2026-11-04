"""
Invoice Details Component.

Renders structured high-level invoice metadata cards:
- Supplier Name
- Invoice Number
- Invoice Date
- Currency
- Subtotal, Tax Amount, and Grand Total
Using Bootstrap Icons and high-contrast, accessible typography with zero emojis.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import streamlit as st

from src.utils import format_currency


def render_invoice_details(invoice_data: Optional[Dict[str, Any]]) -> None:
    """
    Renders structured summary cards for top-level invoice metadata and financials.

    Args:
        invoice_data: Cleaned invoice dictionary.
    """
    if not invoice_data:
        st.info("No invoice data available.")
        return

    currency = invoice_data.get("currency") or "NPR"
    supplier = invoice_data.get("supplier_name")
    invoice_number = invoice_data.get("invoice_number")
    invoice_date = invoice_data.get("invoice_date")

    subtotal = invoice_data.get("subtotal")
    tax_amount = invoice_data.get("tax_amount")
    total_amount = invoice_data.get("total_amount")

    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 14px;">
            <i class="bi bi-file-earmark-text" style="color: #2563eb; font-size: 1.25rem;"></i>
            <h4 style="color: #0f172a; font-weight: 700; margin: 0; font-size: 1.15rem; letter-spacing: -0.01em;">
                Invoice Overview
            </h4>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top Row: Supplier, Invoice Number, Date, Currency
    col1, col2, col3, col4 = st.columns(4)

    def _render_meta_card(title: str, icon_class: str, value: Optional[str]) -> str:
        if value:
            return f"""
            <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px 14px;">
                <div style="font-size: 0.78rem; color: #475569; font-weight: 600; display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                    <i class="{icon_class}" style="color: #2563eb;"></i>
                    <span>{title}</span>
                </div>
                <div style="font-size: 1.05rem; color: #0f172a; font-weight: 700; word-break: break-word;">
                    {value}
                </div>
            </div>
            """
        else:
            return f"""
            <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 12px 14px;">
                <div style="font-size: 0.78rem; color: #991b1b; font-weight: 600; display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                    <i class="{icon_class}"></i>
                    <span>{title}</span>
                </div>
                <div style="font-size: 0.92rem; color: #dc2626; font-weight: 600; display: flex; align-items: center; gap: 4px;">
                    <i class="bi bi-exclamation-circle-fill" style="font-size: 0.85rem;"></i>
                    <span>Not detected</span>
                </div>
            </div>
            """

    with col1:
        st.markdown(
            _render_meta_card("Supplier Name", "bi bi-building", str(supplier) if supplier else None),
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            _render_meta_card("Invoice Number", "bi bi-hash", str(invoice_number) if invoice_number else None),
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            _render_meta_card("Invoice Date", "bi bi-calendar3", str(invoice_date) if invoice_date else None),
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            _render_meta_card("Currency", "bi bi-currency-exchange", str(currency).upper()),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Second Row: Financial Summary (Subtotal, Tax, Total)
    fcol1, fcol2, fcol3 = st.columns(3)

    with fcol1:
        sub_str = format_currency(subtotal, currency) if subtotal is not None else None
        if sub_str and sub_str != "Not specified":
            st.markdown(
                f"""
                <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px 16px;">
                    <div style="font-size: 0.8rem; color: #475569; font-weight: 600; display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                        <i class="bi bi-calculator" style="color: #2563eb;"></i>
                        <span>Subtotal</span>
                    </div>
                    <div style="font-size: 1.25rem; color: #0f172a; font-weight: 700;">
                        {sub_str}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="background-color: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 14px 16px;">
                    <div style="font-size: 0.8rem; color: #92400e; font-weight: 600; margin-bottom: 4px;">
                        Subtotal
                    </div>
                    <div style="font-size: 1.1rem; color: #b45309; font-weight: 700; display: flex; align-items: center; gap: 6px;">
                        <i class="bi bi-exclamation-triangle-fill" style="font-size: 0.95rem;"></i>
                        <span>Missing</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with fcol2:
        tax_str = format_currency(tax_amount, currency) if tax_amount is not None else None
        st.markdown(
            f"""
            <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px 16px;">
                <div style="font-size: 0.8rem; color: #475569; font-weight: 600; display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                    <i class="bi bi-percent" style="color: #2563eb;"></i>
                    <span>Tax Amount (VAT)</span>
                </div>
                <div style="font-size: 1.25rem; color: #0f172a; font-weight: 700;">
                    {tax_str if tax_str and tax_str != "Not specified" else "0.00 / Exempt"}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with fcol3:
        tot_str = format_currency(total_amount, currency) if total_amount is not None else None
        if tot_str and tot_str != "Not specified":
            st.markdown(
                f"""
                <div style="background-color: #eff6ff; border: 1.5px solid #93c5fd; border-radius: 8px; padding: 14px 16px;">
                    <div style="font-size: 0.8rem; color: #1e40af; font-weight: 700; display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                        <i class="bi bi-cash-stack" style="color: #2563eb;"></i>
                        <span>Grand Total Amount</span>
                    </div>
                    <div style="font-size: 1.35rem; color: #1e3a8a; font-weight: 800;">
                        {tot_str}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="background-color: #fef2f2; border: 1.5px solid #fecaca; border-radius: 8px; padding: 14px 16px;">
                    <div style="font-size: 0.8rem; color: #991b1b; font-weight: 700; margin-bottom: 4px;">
                        Grand Total Amount
                    </div>
                    <div style="font-size: 1.15rem; color: #dc2626; font-weight: 700; display: flex; align-items: center; gap: 6px;">
                        <i class="bi bi-exclamation-triangle-fill" style="font-size: 0.95rem;"></i>
                        <span>Missing</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

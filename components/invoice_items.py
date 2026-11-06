"""
Invoice Items Component.

Renders:
1. Formatted line items table with quantity, unit price, and calculated line totals.
2. Interactive invoice editor allowing modification of:
   - Invoice metadata (Supplier, number, date, currency)
   - Line items (descriptions, quantities, unit prices, adding/removing rows)
   - Financial totals (subtotal, tax, grand total)
3. One-click instant offline revalidation via `revalidate_edited_invoice()` with zero emojis.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.services import revalidate_edited_invoice
from src.utils import (
    build_items_dataframe,
    calculate_item_line_total,
    format_currency,
)


def render_invoice_items(
    invoice_data: Optional[Dict[str, Any]],
    validation_result: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Renders invoice items table and interactive editor with live revalidation.

    Args:
        invoice_data: Current extracted invoice dictionary.
        validation_result: Current validation result dictionary.
    """
    if not invoice_data:
        st.info("No items data available.")
        return

    items = invoice_data.get("items") or []
    currency = invoice_data.get("currency") or "NPR"

    tab_view, tab_edit = st.tabs(["Line Items Table", "Edit Invoice & Live Revalidate"])

    # Formatted table view tab
    with tab_view:
        if not items:
            st.markdown(
                """
                <div style="background-color: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 12px 14px; color: #92400e; font-size: 0.88rem; display: flex; align-items: center; gap: 8px;">
                    <i class="bi bi-exclamation-triangle-fill" style="color: #d97706;"></i>
                    <span>No line items detected in this invoice.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            df = build_items_dataframe(items, currency=currency)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
            )

            # Summary Footer Bar
            item_count = len(items)
            valid_items_sum = sum(
                float(it.get("calculated_line_total") or 0.0)
                for it in items
                if isinstance(it, dict) and it.get("calculated_line_total") is not None
            )

            col_cnt, col_sum = st.columns(2)
            with col_cnt:
                st.markdown(
                    f"""
                    <div style="font-size: 0.82rem; color: #475569; display: flex; align-items: center; gap: 6px;">
                        <i class="bi bi-list-check" style="color: #2563eb;"></i>
                        <span>Total line items: <strong style="color: #0f172a;">{item_count}</strong></span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_sum:
                st.markdown(
                    f"""
                    <div style="font-size: 0.82rem; color: #475569; display: flex; align-items: center; gap: 6px; justify-content: flex-end;">
                        <i class="bi bi-calculator" style="color: #2563eb;"></i>
                        <span>Calculated Items Sum: <strong style="color: #0f172a;">{format_currency(valid_items_sum, currency)}</strong></span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # Interactive edit & revalidate tab
    with tab_edit:
        st.markdown(
            """
            <div style="background-color: #f0f7ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px 14px; margin-bottom: 16px; color: #1e3a8a; font-size: 0.85rem; display: flex; align-items: flex-start; gap: 8px;">
                <i class="bi bi-info-circle-fill" style="color: #2563eb; font-size: 1rem; margin-top: 1px;"></i>
                <div>
                    <strong>Live Offline Revalidation:</strong> Modify any detected field, add or delete rows, or correct OCR errors.
                    Revalidation executes 100% locally with zero Google Gemini AI API calls.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("invoice_edit_form"):
            st.markdown(
                """
                <div style="font-weight: 700; font-size: 0.92rem; color: #0f172a; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                    <i class="bi bi-card-heading" style="color: #2563eb;"></i>
                    <span>1. Header Information</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)

            with meta_col1:
                edit_supplier = st.text_input(
                    "Supplier Name",
                    value=invoice_data.get("supplier_name") or "",
                    placeholder="e.g. Acme Corporation",
                )
            with meta_col2:
                edit_inv_num = st.text_input(
                    "Invoice Number",
                    value=invoice_data.get("invoice_number") or "",
                    placeholder="e.g. INV-2024-001",
                )
            with meta_col3:
                edit_date = st.text_input(
                    "Invoice Date (YYYY-MM-DD)",
                    value=invoice_data.get("invoice_date") or "",
                    placeholder="e.g. 2024-03-24",
                )
            with meta_col4:
                edit_currency = st.text_input(
                    "Currency",
                    value=invoice_data.get("currency") or "NPR",
                    placeholder="e.g. NPR, USD, EUR",
                )

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="font-weight: 700; font-size: 0.92rem; color: #0f172a; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                    <i class="bi bi-table" style="color: #2563eb;"></i>
                    <span>2. Line Items (Add, edit, or delete rows)</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Prepare items for data editor
            editor_rows: List[Dict[str, Any]] = []
            for item in items:
                if isinstance(item, dict):
                    editor_rows.append(
                        {
                            "description": item.get("description") or "",
                            "quantity": float(item["quantity"]) if item.get("quantity") is not None else 1.0,
                            "unit_price": float(item["unit_price"]) if item.get("unit_price") is not None else 0.0,
                        }
                    )

            if not editor_rows:
                editor_rows = [{"description": "", "quantity": 1.0, "unit_price": 0.0}]

            items_df = pd.DataFrame(editor_rows)

            edited_df = st.data_editor(
                items_df,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "description": st.column_config.TextColumn(
                        "Item Description",
                        required=True,
                        width="large",
                    ),
                    "quantity": st.column_config.NumberColumn(
                        "Quantity",
                        min_value=0.01,
                        step=1.0,
                        format="%.2f",
                        required=True,
                    ),
                    "unit_price": st.column_config.NumberColumn(
                        "Unit Price",
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                        required=True,
                    ),
                },
                key="items_data_editor",
            )

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.markdown(
                """
                <div style="font-weight: 700; font-size: 0.92rem; color: #0f172a; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                    <i class="bi bi-wallet2" style="color: #2563eb;"></i>
                    <span>3. Financial Totals</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            fin_col1, fin_col2, fin_col3 = st.columns(3)

            current_subtotal = invoice_data.get("subtotal")
            current_tax = invoice_data.get("tax_amount")
            current_total = invoice_data.get("total_amount")

            with fin_col1:
                edit_subtotal_str = st.text_input(
                    "Subtotal",
                    value=str(current_subtotal) if current_subtotal is not None else "",
                    help="Numeric subtotal before tax",
                )
            with fin_col2:
                edit_tax_str = st.text_input(
                    "Tax Amount (VAT)",
                    value=str(current_tax) if current_tax is not None else "0.00",
                    help="Numeric tax amount",
                )
            with fin_col3:
                edit_total_str = st.text_input(
                    "Grand Total Amount",
                    value=str(current_total) if current_total is not None else "",
                    help="Numeric grand total",
                )

            st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

            submit_revalidate = st.form_submit_button(
                "Validate Updated Invoice",
                type="primary",
                use_container_width=True,
            )

        if submit_revalidate:
            # Reconstruct item list from edited_df
            new_items = []
            for _, row in edited_df.iterrows():
                desc = str(row.get("description", "")).strip()
                qty_raw = row.get("quantity")
                price_raw = row.get("unit_price")

                # Only include rows that have content
                if desc or qty_raw is not None or price_raw is not None:
                    new_items.append(
                        {
                            "description": desc if desc else None,
                            "quantity": float(qty_raw) if qty_raw is not None else None,
                            "unit_price": float(price_raw) if price_raw is not None else None,
                        }
                    )

            # Parse financial totals
            subtotal_val = None
            if edit_subtotal_str and edit_subtotal_str.strip():
                try:
                    subtotal_val = float(edit_subtotal_str.replace(",", "").strip())
                except ValueError:
                    subtotal_val = edit_subtotal_str.strip()

            tax_val = None
            if edit_tax_str and edit_tax_str.strip():
                try:
                    tax_val = float(edit_tax_str.replace(",", "").strip())
                except ValueError:
                    tax_val = edit_tax_str.strip()

            total_val = None
            if edit_total_str and edit_total_str.strip():
                try:
                    total_val = float(edit_total_str.replace(",", "").strip())
                except ValueError:
                    total_val = edit_total_str.strip()

            updated_invoice_payload: Dict[str, Any] = {
                "supplier_name": edit_supplier.strip() if edit_supplier.strip() else None,
                "invoice_number": edit_inv_num.strip() if edit_inv_num.strip() else None,
                "invoice_date": edit_date.strip() if edit_date.strip() else None,
                "currency": edit_currency.strip() if edit_currency.strip() else "NPR",
                "items": new_items,
                "subtotal": subtotal_val,
                "tax_amount": tax_val,
                "total_amount": total_val,
            }

            # Retain existing metadata if present
            if "_metadata" in invoice_data:
                updated_invoice_payload["_metadata"] = invoice_data["_metadata"]

            # Trigger core revalidation
            reval_res = revalidate_edited_invoice(updated_invoice_payload)

            # Update session state
            st.session_state["extracted_data"] = reval_res["invoice_data"]
            st.session_state["validation_result"] = reval_res["validation"]

            # Update recent history if exists
            filename = st.session_state.get("current_filename") or "invoice.png"
            history = st.session_state.get("session_history", [])
            for h in history:
                if h.get("filename") == filename:
                    h["is_valid"] = reval_res["validation"]["is_valid"]
                    h["invoice_number"] = reval_res["invoice_data"].get("invoice_number") or "Not detected"
                    h["supplier_name"] = reval_res["invoice_data"].get("supplier_name") or "Not detected"
                    h["total_amount"] = reval_res["invoice_data"].get("total_amount")
                    h["currency"] = reval_res["invoice_data"].get("currency") or "NPR"
                    h["errors_count"] = len(reval_res["validation"].get("errors", []))
                    h["warnings_count"] = len(reval_res["validation"].get("warnings", []))
                    break

            st.toast("Invoice updated and successfully revalidated!")
            st.rerun()

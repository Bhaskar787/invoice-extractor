"""
InvoiceAI – Smart Invoice Extraction Web Application.

A professional, interactive Streamlit application for AI-powered invoice
data extraction using Google Gemini Multimodal Vision AI and independent
financial validation for Rivertech Supplies Ltd.

Entry point:
    streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from components import (
    render_header,
    render_invoice_details,
    render_invoice_items,
    render_invoice_preview,
    render_json_export,
    render_sidebar,
    render_uploader,
    render_validation_panel,
)
from src.services import get_gemini_connection_status

# =============================================================================
# STREAMLIT PAGE CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="InvoiceAI – Smart Invoice Extraction",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# BOOTSTRAP ICONS & GLOBAL CUSTOM CSS STYLING
# =============================================================================
st.markdown(
    """
    <!-- Bootstrap Icons CDN -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    
    <style>
        /* Base typography & accessibility */
        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
            max-width: 1350px;
        }
        
        /* High-contrast headings */
        h1, h2, h3, h4, h5 {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #0f172a !important;
            letter-spacing: -0.015em;
        }
        
        /* Metric card styling */
        [data-testid="stMetric"] {
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 8px !important;
            padding: 12px 16px !important;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.8rem !important;
            color: #475569 !important;
            font-weight: 600 !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.35rem !important;
            color: #0f172a !important;
            font-weight: 700 !important;
        }
        
        /* Primary and secondary buttons */
        div.stButton > button {
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.88rem;
            transition: all 0.15s ease-in-out;
        }
        
        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            border-bottom: 2px solid #e2e8f0;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 8px 16px;
            border-radius: 6px 6px 0 0;
            font-weight: 600;
            font-size: 0.9rem;
            color: #475569;
        }
        .stTabs [aria-selected="true"] {
            color: #2563eb !important;
            border-bottom-color: #2563eb !important;
        }

        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #f8fafc;
            border-right: 1px solid #e2e8f0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
def init_session_state() -> None:
    """Initializes all required session state variables."""
    defaults = {
        "session_history": [],
        "current_file_bytes": None,
        "current_filename": None,
        "extracted_data": None,
        "validation_result": None,
        "processing_status": "idle",  # "idle" | "processing" | "success" | "error"
        "error_message": None,
        "nav_radio_selection": "Dashboard",
        "pending_page": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()


# =============================================================================
# PAGE 1: DASHBOARD
# =============================================================================
def render_dashboard_page() -> None:
    """Renders the executive dashboard overview with session statistics and recent files."""
    st.markdown(
        """
        <div style="margin-bottom: 18px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <i class="bi bi-speedometer2" style="color: #2563eb; font-size: 1.5rem;"></i>
                <h2 style="font-size: 1.55rem; font-weight: 700; color: #0f172a; margin: 0;">
                    Overview Dashboard
                </h2>
            </div>
            <p style="color: #475569; font-size: 0.88rem; margin: 4px 0 0 0; font-weight: 400;">
                Real-time extraction metrics, processing activity, and invoice status audit.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    history: List[Dict[str, Any]] = st.session_state.get("session_history", [])
    total_invoices = len(history)
    valid_count = sum(1 for h in history if h.get("is_valid"))
    review_count = sum(1 for h in history if not h.get("is_valid") and h.get("errors_count", 0) == 0)
    failed_count = sum(1 for h in history if not h.get("is_valid") and h.get("errors_count", 0) > 0)

    # 4 Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(label="Total Processed", value=total_invoices)
    with m2:
        st.metric(label="Valid Invoices", value=valid_count)
    with m3:
        st.metric(label="Needs Review", value=review_count)
    with m4:
        st.metric(label="Validation Errors", value=failed_count)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Action Banner & Quick Load
    act_col1, act_col2 = st.columns([2, 1])

    with act_col1:
        st.markdown(
            """
            <div style="background-color: #f0f7ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 16px 20px;">
                <div style="color: #1e40af; margin: 0 0 6px 0; font-size: 1.05rem; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                    <i class="bi bi-cloud-arrow-up-fill" style="color: #2563eb;"></i>
                    <span>Ready to extract an invoice?</span>
                </div>
                <p style="color: #1e3a8a; font-size: 0.86rem; margin: 0 0 14px 0;">
                    Upload an invoice image to run Google Gemini multimodal vision extraction and automated financial checks.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        if st.button("Upload New Invoice", type="primary", use_container_width=False):
            st.session_state["pending_page"] = "Extract Invoice"
            st.rerun()

    with act_col2:
        st.markdown(
            """
            <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 10px; padding: 16px 20px;">
                <div style="color: #0f172a; margin: 0 0 6px 0; font-size: 1.05rem; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                    <i class="bi bi-file-earmark-check" style="color: #16a34a;"></i>
                    <span>Try Sample Invoice</span>
                </div>
                <p style="color: #475569; font-size: 0.86rem; margin: 0 0 14px 0;">
                    Load the pre-bundled Rivertech Supplies sample invoice (samples/invoice.png).
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        sample_path = Path("samples/invoice.png")
        if sample_path.exists():
            if st.button("Load Sample Invoice", use_container_width=False):
                try:
                    with open(sample_path, "rb") as f:
                        sample_bytes = f.read()
                    st.session_state["current_file_bytes"] = sample_bytes
                    st.session_state["current_filename"] = "invoice.png"
                    st.session_state["extracted_data"] = None
                    st.session_state["validation_result"] = None
                    st.session_state["pending_page"] = "Extract Invoice"
                    st.toast("Loaded samples/invoice.png successfully!")
                    st.rerun()
                except Exception as err:
                    st.error(f"Failed to load sample: {err}")
        else:
            st.caption("No sample invoice found at samples/invoice.png.")

    st.markdown("<div style='height: 22px;'></div>", unsafe_allow_html=True)

    # Recent Extractions Table
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
            <i class="bi bi-clock-history" style="color: #2563eb; font-size: 1.15rem;"></i>
            <h3 style="font-size: 1.15rem; font-weight: 700; color: #0f172a; margin: 0;">
                Recent Session Extractions
            </h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not history:
        st.markdown(
            """
            <div style="border: 2px dashed #cbd5e1; border-radius: 10px; padding: 36px 16px; text-align: center; background-color: #f8fafc;">
                <i class="bi bi-inbox" style="font-size: 2.2rem; color: #94a3b8;"></i>
                <p style="margin: 8px 0 0 0; color: #1e293b; font-weight: 600;">
                    No invoices extracted yet in this session
                </p>
                <p style="margin: 4px 0 0 0; color: #64748b; font-size: 0.82rem;">
                    Navigate to <strong>Extract Invoice</strong> or click <strong>Upload New Invoice</strong> above to start.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        table_rows = []
        for rec in history:
            is_val = rec.get("is_valid", False)
            status_str = "Valid" if is_val else f"Invalid ({rec.get('errors_count', 0)} errors)"
            tot = rec.get("total_amount")
            curr = rec.get("currency") or "NPR"
            tot_str = f"{curr} {tot:,.2f}" if isinstance(tot, (int, float)) else "Not specified"

            table_rows.append(
                {
                    "Timestamp": rec.get("timestamp"),
                    "Filename": rec.get("filename"),
                    "Invoice #": rec.get("invoice_number"),
                    "Supplier": rec.get("supplier_name"),
                    "Total Amount": tot_str,
                    "Validation Status": status_str,
                }
            )

        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)


# =============================================================================
# PAGE 2: EXTRACT INVOICE
# =============================================================================
def render_extract_page() -> None:
    """Renders the invoice upload and extraction interface."""
    st.markdown(
        """
        <div style="margin-bottom: 18px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <i class="bi bi-cloud-arrow-up" style="color: #2563eb; font-size: 1.5rem;"></i>
                <h2 style="font-size: 1.55rem; font-weight: 700; color: #0f172a; margin: 0;">
                    Extract Invoice Data
                </h2>
            </div>
            <p style="color: #475569; font-size: 0.88rem; margin: 4px 0 0 0;">
                Upload an invoice image or load a sample to trigger Google Gemini AI extraction.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_upload, col_preview = st.columns([1, 1], gap="large")

    with col_upload:
        st.markdown(
            """
            <div style="font-weight: 700; font-size: 0.95rem; color: #0f172a; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                <i class="bi bi-upload" style="color: #2563eb;"></i>
                <span>1. Select & Upload Image</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_uploader()

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px;">
                <div style="font-weight: 700; font-size: 0.84rem; color: #0f172a; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                    <i class="bi bi-info-circle-fill" style="color: #2563eb;"></i>
                    <span>Extraction Specifications</span>
                </div>
                <ul style="margin: 0; padding-left: 20px; font-size: 0.8rem; color: #475569; line-height: 1.6;">
                    <li><strong>Supported formats:</strong> PNG, JPG, JPEG, WEBP (Max 20 MB).</li>
                    <li><strong>Extracted fields:</strong> Supplier Name, Invoice Number, Invoice Date, Currency, Line Items (description, quantity, unit price), Subtotal, Tax, Total Amount.</li>
                    <li><strong>AI Engine:</strong> Google Gemini Multimodal Vision API.</li>
                    <li><strong>Post-Processing:</strong> Automatic arithmetic reconciliation and ISO standardization.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_preview:
        st.markdown(
            """
            <div style="font-weight: 700; font-size: 0.95rem; color: #0f172a; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                <i class="bi bi-image" style="color: #2563eb;"></i>
                <span>2. Invoice Preview</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        image_bytes = st.session_state.get("current_file_bytes")
        filename = st.session_state.get("current_filename")
        render_invoice_preview(image_bytes=image_bytes, filename=filename)


# =============================================================================
# PAGE 3: EXTRACTION RESULTS
# =============================================================================
def render_results_page() -> None:
    """Renders structured extraction results, items table, editor, validation panel, and JSON."""
    extracted_data = st.session_state.get("extracted_data")
    validation_result = st.session_state.get("validation_result")
    image_bytes = st.session_state.get("current_file_bytes")
    filename = st.session_state.get("current_filename")

    if not extracted_data:
        st.markdown(
            """
            <div style="margin-bottom: 18px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <i class="bi bi-receipt-cutoff" style="color: #2563eb; font-size: 1.5rem;"></i>
                    <h2 style="font-size: 1.55rem; font-weight: 700; color: #0f172a; margin: 0;">
                        Extraction Results
                    </h2>
                </div>
                <p style="color: #475569; font-size: 0.88rem; margin: 4px 0 0 0;">
                    No invoice has been extracted yet in this session.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div style="border: 2px dashed #cbd5e1; border-radius: 10px; padding: 48px 16px; text-align: center; background-color: #f8fafc;">
                <i class="bi bi-file-earmark-x" style="font-size: 2.4rem; color: #94a3b8;"></i>
                <p style="margin: 10px 0 0 0; color: #1e293b; font-weight: 600;">
                    No Extraction Data Available
                </p>
                <p style="margin: 4px 0 16px 0; color: #64748b; font-size: 0.84rem;">
                    Please upload an invoice image and click "Extract Invoice with Gemini AI".
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Go to Extract Invoice", type="primary"):
            st.session_state["pending_page"] = "Extract Invoice"
            st.rerun()
        return

    # Results Header
    st.markdown(
        """
        <div style="margin-bottom: 16px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <i class="bi bi-receipt-cutoff" style="color: #2563eb; font-size: 1.5rem;"></i>
                <h2 style="font-size: 1.55rem; font-weight: 700; color: #0f172a; margin: 0;">
                    Extraction & Validation Results
                </h2>
            </div>
            <p style="color: #475569; font-size: 0.88rem; margin: 4px 0 0 0;">
                Structured invoice fields, line items table, interactive corrections, and JSON export.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. High-level Metadata Summary Cards
    render_invoice_details(extracted_data)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # 2. Main Two-Column View:
    # Left: Invoice Preview + Validation Panel
    # Right: Line Items & Live Editor + JSON Export
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown(
            """
            <div style="font-weight: 700; font-size: 0.95rem; color: #0f172a; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                <i class="bi bi-shield-check" style="color: #2563eb;"></i>
                <span>Validation & Source Image</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Validation Status & Rule Checks
        render_validation_panel(validation_result, invoice_data=extracted_data)

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        # Source Invoice Image Preview
        render_invoice_preview(image_bytes=image_bytes, filename=filename)

    with col_right:
        st.markdown(
            """
            <div style="font-weight: 700; font-size: 0.95rem; color: #0f172a; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                <i class="bi bi-table" style="color: #2563eb;"></i>
                <span>Line Items & Live Corrections</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Line Items Table & Live Revalidation Form
        render_invoice_items(extracted_data, validation_result)

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="font-weight: 700; font-size: 0.95rem; color: #0f172a; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                <i class="bi bi-filetype-json" style="color: #2563eb;"></i>
                <span>Structured JSON & Download</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # JSON Viewer and Download Button
        render_json_export(extracted_data, validation_result, filename=filename)


# =============================================================================
# PAGE 4: ABOUT THE APPLICATION
# =============================================================================
def render_about_page() -> None:
    """Renders project documentation, architecture, and engineering overview."""
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <i class="bi bi-info-circle" style="color: #2563eb; font-size: 1.5rem;"></i>
                <h2 style="font-size: 1.55rem; font-weight: 700; color: #0f172a; margin: 0;">
                    About InvoiceAI
                </h2>
            </div>
            <p style="color: #475569; font-size: 0.88rem; margin: 4px 0 0 0;">
                Technical Overview, Architecture, and Rivertech Supplies Ltd. Assignment Context.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        ### Background: Rivertech Supplies Ltd.
        This application solves an automated financial accounting challenge for **Rivertech Supplies Ltd.** Invoices arrive in various visual formats (PNG, JPG, WEBP) requiring accurate extraction of critical financial data and automated arithmetic verification before ingestion into downstream accounting and ERP systems.

        ---

        ### Technical Architecture & Data Pipeline
        The system follows a strict layered architecture:
        1. **Presentation Layer (Streamlit)**:
           - User-friendly web interface with drag-and-drop uploading, image inspection, structured cards, interactive editing (`st.data_editor`), and JSON export.
           - Dual operation: Can be run as a Web App (`streamlit run app.py`) or as a CLI tool (`python main.py samples/invoice.png`).
        2. **Service Layer (`src/services.py`)**:
           - Acts as the single coordinator. Decouples UI presentation from backend extraction and validation engines.
           - Provides live status checks, upload preprocessing, and **zero-AI offline revalidation**.
        3. **Extraction Engine (`src/extractor.py`)**:
           - Direct Google Gemini Multimodal Vision API invocation (`gemini-3-flash-preview` with automatic fallbacks).
           - Robust prompt engineering instructing Gemini to return strict, typed JSON conforming to our schema.
           - Defensive cleaning pipeline (`clean_invoice_data`): Strips currency symbols (`NPR`, `$`), standardizes dates (ISO 8601), and handles OCR artifacts.
        4. **Validation Engine (`src/validator.py`)**:
           - **Single source of truth** for business and financial rules.
           - Verifies:
             - Mandatory fields (Supplier, Invoice Number, Date, Currency, Subtotal, Total).
             - Quantity strictly positive (> 0), unit price non-negative (>= 0).
             - Independent item line total computation: Quantity * Unit Price.
             - Items Sum = Subtotal (tolerance <= 0.05).
             - Subtotal + Tax = Grand Total (tolerance <= 0.05).
             - Calculated grand total verification.

        ---

        ### Key Reliability & Security Standards
        - **Defensive Type Safety**: Explicitly rejects booleans masquerading as numbers (`True == 1`), `NaN`, and `Infinity`.
        - **Zero AI Calls on Edit**: Editing invoice fields runs 100% offline via `revalidate_edited_invoice()`, ensuring instant response times and 0 API quota consumption.
        - **Secret Protection**: API keys are managed strictly via `.env` with `python-dotenv` and masked in all UI displays (`AIza...4xY`).
        - **Comprehensive Test Coverage**: Tested across unit, integration, edge cases, and CLI behaviors using `pytest`.
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# MAIN APPLICATION ROUTER
# =============================================================================
def main() -> None:
    """Main application loop."""
    render_header()
    selected_page = render_sidebar()

    if selected_page == "Dashboard":
        render_dashboard_page()
    elif selected_page == "Extract Invoice":
        render_extract_page()
    elif selected_page == "Extraction Results":
        render_results_page()
    elif selected_page == "About the Application":
        render_about_page()
    else:
        render_dashboard_page()


if __name__ == "__main__":
    main()

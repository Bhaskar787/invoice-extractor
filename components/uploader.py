"""
Uploader Component.

Handles drag-and-drop file uploading, file validation,
and AI extraction execution with clear progress feedback and zero emojis.
"""

from __future__ import annotations

import io
from pathlib import Path
from PIL import Image
import streamlit as st

from src.exceptions import (
    APIExtractionError,
    ConfigurationError,
    ImageValidationError,
    InvoiceExtractorError,
    JSONParsingError,
)
from src.extractor import MAX_IMAGE_FILE_SIZE_BYTES, SUPPORTED_MIME_TYPES
from src.services import (
    create_session_history_record,
    get_gemini_connection_status,
    process_invoice_upload,
)


def render_uploader() -> None:
    """Renders the file uploader and extraction action controls."""
    uploaded_file = st.file_uploader(
        "Upload Invoice Image",
        type=["png", "jpg", "jpeg", "webp"],
        help="Upload an invoice image (PNG, JPG, JPEG, WEBP). Maximum size: 20 MB.",
        key="invoice_file_uploader",
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        filename = uploaded_file.name

        # If user uploaded a new/different file, update session state
        if st.session_state.get("current_filename") != filename:
            st.session_state["current_file_bytes"] = file_bytes
            st.session_state["current_filename"] = filename
            st.session_state["extracted_data"] = None
            st.session_state["validation_result"] = None
            st.session_state["processing_status"] = "idle"
            st.session_state["error_message"] = None

    # Handle file removal or empty state
    if uploaded_file is None and st.session_state.get("current_file_bytes") is not None:
        if st.button("Clear Uploaded Image", type="secondary", use_container_width=True):
            st.session_state["current_file_bytes"] = None
            st.session_state["current_filename"] = None
            st.session_state["extracted_data"] = None
            st.session_state["validation_result"] = None
            st.session_state["processing_status"] = "idle"
            st.session_state["error_message"] = None
            st.rerun()

    has_file = st.session_state.get("current_file_bytes") is not None
    api_status = get_gemini_connection_status()

    # Pre-flight upload validation
    validation_error = None
    if has_file:
        raw_bytes = st.session_state["current_file_bytes"]
        fname = st.session_state["current_filename"] or "invoice.png"

        if len(raw_bytes) > MAX_IMAGE_FILE_SIZE_BYTES:
            validation_error = f"File exceeds maximum allowed size of 20 MB (current size: {len(raw_bytes) / (1024*1024):.1f} MB)."
        else:
            ext = Path(fname).suffix.lower()
            if ext not in SUPPORTED_MIME_TYPES:
                validation_error = f"Unsupported file extension '{ext}'. Supported: {', '.join(SUPPORTED_MIME_TYPES.keys())}"
            else:
                try:
                    with Image.open(io.BytesIO(raw_bytes)) as img:
                        img.verify()
                except Exception as err:
                    validation_error = f"Corrupted or invalid image file: {err}"

    if validation_error:
        st.markdown(
            f"""
            <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 10px 14px; margin-top: 8px; color: #991b1b; font-size: 0.85rem; display: flex; align-items: center; gap: 8px;">
                <i class="bi bi-exclamation-triangle-fill" style="color: #dc2626; font-size: 1rem;"></i>
                <span>{validation_error}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Prominent Extraction Action Button
    can_extract = has_file and (validation_error is None) and api_status["is_configured"]

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    if not api_status["is_configured"]:
        st.markdown(
            """
            <div style="background-color: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 10px 14px; margin-bottom: 10px; color: #92400e; font-size: 0.85rem; display: flex; align-items: center; gap: 8px;">
                <i class="bi bi-exclamation-circle-fill" style="color: #d97706; font-size: 1rem;"></i>
                <span>Google Gemini API key is missing. Please add <code>GEMINI_API_KEY</code> to your <code>.env</code> file.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    button_label = "Extract Invoice with Gemini AI"
    extract_clicked = st.button(
        button_label,
        type="primary",
        disabled=not can_extract,
        use_container_width=True,
        key="btn_trigger_extraction",
    )

    if extract_clicked and can_extract:
        file_bytes = st.session_state["current_file_bytes"]
        filename = st.session_state["current_filename"]

        st.session_state["processing_status"] = "processing"
        st.session_state["error_message"] = None

        with st.status("Extracting invoice data with Google Gemini...", expanded=True) as status_box:
            try:
                st.write("Step 1/4: Reading and validating invoice image...")
                st.write(f"Step 2/4: Invoking Gemini Vision AI ({api_status['model']})...")

                result = process_invoice_upload(
                    image_bytes=file_bytes,
                    filename=filename,
                )

                st.write("Step 3/4: Sanitizing line items and cleaning data fields...")
                st.write("Step 4/4: Performing independent financial arithmetic validation...")

                st.session_state["extracted_data"] = result["invoice_data"]
                st.session_state["validation_result"] = result["validation"]
                st.session_state["processing_status"] = "success"

                # Record into session history
                history_record = create_session_history_record(
                    filename=filename,
                    invoice_data=result["invoice_data"],
                    validation=result["validation"],
                )
                if "session_history" not in st.session_state:
                    st.session_state["session_history"] = []
                st.session_state["session_history"].insert(0, history_record)

                status_box.update(label="Extraction & Validation Complete", state="complete", expanded=False)

                # Automatically switch to Extraction Results page
                st.session_state["active_page"] = "Extraction Results"
                st.rerun()

            except ImageValidationError as err:
                status_box.update(label="Image Validation Failed", state="error", expanded=True)
                st.error(f"[Invalid Image] {err}")
                st.session_state["error_message"] = str(err)
                st.session_state["processing_status"] = "error"

            except ConfigurationError as err:
                status_box.update(label="Configuration Error", state="error", expanded=True)
                st.error(f"[Configuration Error] {err}")
                st.session_state["error_message"] = str(err)
                st.session_state["processing_status"] = "error"

            except APIExtractionError as err:
                status_box.update(label="Gemini API Error", state="error", expanded=True)
                st.error(f"[Gemini API Error] {err}")
                st.session_state["error_message"] = str(err)
                st.session_state["processing_status"] = "error"

            except JSONParsingError as err:
                status_box.update(label="AI Parsing Error", state="error", expanded=True)
                st.error(f"[AI Parsing Error] {err}")
                st.session_state["error_message"] = str(err)
                st.session_state["processing_status"] = "error"

            except Exception as err:
                status_box.update(label="Unexpected Error", state="error", expanded=True)
                st.error(f"[Unexpected Error] An unexpected error occurred: {err}")
                st.session_state["error_message"] = str(err)
                st.session_state["processing_status"] = "error"

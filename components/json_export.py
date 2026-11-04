"""
JSON Export Component.

Renders:
1. Formatted, syntax-highlighted JSON viewer (`st.json`).
2. One-click JSON download button (`st.download_button`).
3. Payload metadata with Bootstrap Icons and zero emojis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import streamlit as st

from src.utils import generate_export_payload


def render_json_export(
    invoice_data: Optional[Dict[str, Any]],
    validation_result: Optional[Dict[str, Any]],
    filename: Optional[str] = None,
) -> None:
    """
    Renders structured JSON viewer and download actions.

    Args:
        invoice_data: Extracted invoice dictionary.
        validation_result: Validation results dictionary.
        filename: Original image filename to derive export filename.
    """
    if not invoice_data:
        st.info("No JSON data to export.")
        return

    # Derive export filename
    base_name = "invoice"
    if filename:
        stem = Path(filename).stem
        if stem:
            base_name = stem
    export_filename = f"{base_name}_extracted.json"

    # Generate standardized payload
    json_str = generate_export_payload(
        invoice_data=invoice_data,
        validation=validation_result or {},
    )

    size_kb = len(json_str.encode("utf-8")) / 1024

    col_meta, col_btn = st.columns([2, 1])

    with col_meta:
        st.markdown(
            f"""
            <div style="font-size: 0.84rem; color: #475569; padding-top: 6px; display: flex; align-items: center; gap: 6px;">
                <i class="bi bi-filetype-json" style="color: #2563eb; font-size: 1.1rem;"></i>
                <span>File: <strong style="color: #0f172a;">{export_filename}</strong> | Size: <strong style="color: #0f172a;">{size_kb:.1f} KB</strong></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_btn:
        st.download_button(
            label="Download JSON File",
            data=json_str,
            file_name=export_filename,
            mime="application/json",
            type="primary",
            use_container_width=True,
            key="btn_download_json_payload",
        )

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Render JSON Viewer in clean container
    st.json(invoice_data, expanded=True)

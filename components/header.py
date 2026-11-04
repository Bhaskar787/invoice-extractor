"""
Header Component.

Renders application branding, title, and live AI connection status using
Bootstrap Icons with high-contrast, accessible typography.
"""

from __future__ import annotations

import streamlit as st
from src.services import get_gemini_connection_status


def render_header() -> None:
    """Renders the top application navigation header and status bar."""
    status = get_gemini_connection_status()

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 6px;">
                <div style="background: linear-gradient(135deg, #2563eb, #1d4ed8); border-radius: 10px; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);">
                    <i class="bi bi-receipt" style="font-size: 1.5rem; color: #ffffff;"></i>
                </div>
                <div>
                    <h1 style="font-size: 1.75rem; font-weight: 700; color: #0f172a; margin: 0; padding: 0; letter-spacing: -0.02em;">
                        InvoiceAI <span style="font-size: 1.05rem; font-weight: 600; color: #2563eb;">Smart Extraction</span>
                    </h1>
                    <p style="font-size: 0.88rem; color: #475569; margin: 2px 0 0 0; font-weight: 400;">
                        Multimodal Document Data Extraction & Financial Arithmetic Verification
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        if status["is_configured"]:
            st.markdown(
                f"""
                <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 8px 12px; text-align: right;">
                    <div style="color: #166534; font-weight: 600; font-size: 0.82rem; display: flex; align-items: center; justify-content: flex-end; gap: 6px;">
                        <i class="bi bi-check-circle-fill" style="color: #16a34a; font-size: 0.8rem;"></i>
                        <span>Gemini AI Connected</span>
                    </div>
                    <div style="color: #64748b; font-size: 0.74rem; margin-top: 2px;">
                        <i class="bi bi-cpu" style="font-size: 0.72rem;"></i> {status['model']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 8px 12px; text-align: right;">
                    <div style="color: #991b1b; font-weight: 600; font-size: 0.82rem; display: flex; align-items: center; justify-content: flex-end; gap: 6px;">
                        <i class="bi bi-exclamation-triangle-fill" style="color: #dc2626; font-size: 0.8rem;"></i>
                        <span>API Key Missing</span>
                    </div>
                    <div style="color: #64748b; font-size: 0.74rem; margin-top: 2px;">
                        Configure in .env file
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<hr style='margin: 10px 0 18px 0; border: none; border-top: 1px solid #e2e8f0;'/>", unsafe_allow_html=True)

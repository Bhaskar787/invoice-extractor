"""
Sidebar Component.

Renders navigation menu, real session statistics, and session reset controls
using Bootstrap Icons and accessible high-contrast styling.
"""

from __future__ import annotations

import streamlit as st


PAGES = [
    "Dashboard",
    "Extract Invoice",
    "Extraction Results",
    "About the Application",
]


def render_sidebar() -> str:
    """
    Renders sidebar navigation and controls.

    Returns:
        str: Selected page name.
    """
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 6px 0 12px 0;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <i class="bi bi-compass" style="color: #2563eb; font-size: 1.15rem;"></i>
                    <h3 style="margin: 0; color: #0f172a; font-weight: 700; font-size: 1.15rem; letter-spacing: -0.01em;">
                        Navigation
                    </h3>
                </div>
                <p style="margin: 3px 0 0 0; font-size: 0.78rem; color: #475569; font-weight: 500;">
                    Rivertech Supplies Ltd. Portal
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        current_page = st.session_state.get("active_page", PAGES[0])
        if current_page not in PAGES:
            current_page = PAGES[0]

        selected_page = st.radio(
            "Select Section",
            PAGES,
            index=PAGES.index(current_page),
            label_visibility="collapsed",
            key="nav_radio_selection",
        )

        # Update session state if page changed
        st.session_state["active_page"] = selected_page

        st.markdown("<hr style='margin: 14px 0; border: none; border-top: 1px solid #cbd5e1;'/>", unsafe_allow_html=True)

        # Session Metrics Card
        history = st.session_state.get("session_history", [])
        total_invoices = len(history)
        valid_invoices = sum(1 for h in history if h.get("is_valid"))
        review_invoices = sum(1 for h in history if not h.get("is_valid"))

        st.markdown(
            f"""
            <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px; margin-bottom: 14px;">
                <div style="font-weight: 700; font-size: 0.82rem; color: #0f172a; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                    <i class="bi bi-activity" style="color: #2563eb;"></i>
                    <span>Session Summary</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 5px; color: #334155;">
                    <span>Total Processed:</span>
                    <strong style="color: #0f172a;">{total_invoices}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 5px; color: #334155;">
                    <span>Valid Invoices:</span>
                    <strong style="color: #166534;">{valid_invoices}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #334155;">
                    <span>Needs Review:</span>
                    <strong style="color: #b45309;">{review_invoices}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Reset Session Action
        if st.button("Reset Current Session", use_container_width=True, type="secondary"):
            st.session_state["current_file_bytes"] = None
            st.session_state["current_filename"] = None
            st.session_state["extracted_data"] = None
            st.session_state["validation_result"] = None
            st.session_state["processing_status"] = "idle"
            st.session_state["error_message"] = None
            st.session_state["active_page"] = PAGES[0]
            st.rerun()

        st.markdown(
            """
            <div style="margin-top: 20px; font-size: 0.73rem; color: #64748b; text-align: center; line-height: 1.4;">
                <i class="bi bi-cpu"></i> Google Gemini 3 Flash Vision AI<br>
                Python 3.10+ | Pydantic | Streamlit
            </div>
            """,
            unsafe_allow_html=True,
        )

    return selected_page

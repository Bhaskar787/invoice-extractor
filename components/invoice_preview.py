"""
Invoice Preview Component.

Renders responsive image preview of uploaded invoice with zoom expander
and metadata using Bootstrap Icons and clean high-contrast styling.
"""

from __future__ import annotations

import io
from typing import Optional
from PIL import Image
import streamlit as st


def render_invoice_preview(
    image_bytes: Optional[bytes],
    filename: Optional[str] = None,
) -> None:
    """
    Renders an uploaded invoice preview with aspect ratio preservation.

    Args:
        image_bytes: Binary bytes of the uploaded image.
        filename: Optional name of the uploaded file.
    """
    if not image_bytes:
        st.markdown(
            """
            <div style="border: 2px dashed #cbd5e1; border-radius: 10px; padding: 44px 16px; text-align: center; background-color: #f8fafc;">
                <i class="bi bi-card-image" style="font-size: 2.4rem; color: #94a3b8;"></i>
                <p style="margin: 10px 0 0 0; color: #1e293b; font-weight: 600; font-size: 0.95rem;">
                    No invoice uploaded yet
                </p>
                <p style="margin: 4px 0 0 0; color: #64748b; font-size: 0.82rem;">
                    Upload a PNG, JPG, or WEBP image to preview here
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
        width, height = pil_img.size
        format_name = pil_img.format or "Image"
    except Exception:
        width, height = 0, 0
        format_name = "Image"

    file_size_kb = len(image_bytes) / 1024
    size_str = f"{file_size_kb:.1f} KB" if file_size_kb < 1024 else f"{(file_size_kb / 1024):.2f} MB"

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <div style="font-weight: 600; font-size: 0.88rem; color: #0f172a; display: flex; align-items: center; gap: 6px;">
                <i class="bi bi-file-earmark-image" style="color: #2563eb;"></i>
                <span>{filename or 'Uploaded Invoice'}</span>
            </div>
            <span style="font-size: 0.76rem; background-color: #f1f5f9; color: #334155; padding: 2px 8px; border-radius: 4px; border: 1px solid #cbd5e1; font-weight: 500;">
                {format_name} | {width}x{height}px | {size_str}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Standard card preview
    st.image(image_bytes, use_container_width=True)

    # High-detail expander for fine text inspection
    with st.expander("Inspect image full width", expanded=False):
        st.image(image_bytes, use_container_width=True)

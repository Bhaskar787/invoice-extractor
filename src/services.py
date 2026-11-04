"""
Services Module.

Coordinates invoice processing, AI extraction, defensive data cleaning,
live financial revalidation, session history tracking, and API status monitoring.
Acts as the single bridge between Streamlit UI presentation and the core
extractor and validator engines.
"""

from __future__ import annotations

import io
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image, UnidentifiedImageError

from src.config import DEFAULT_MODEL, GEMINI_API_KEY, GEMINI_MODEL, validate_config
from src.exceptions import (
    APIExtractionError,
    ConfigurationError,
    ImageValidationError,
    InvoiceExtractorError,
    JSONParsingError,
)
from src.extractor import (
    MAX_IMAGE_FILE_SIZE_BYTES,
    SUPPORTED_MIME_TYPES,
    clean_invoice_data,
    extract_invoice,
)
from src.validator import validate_invoice


def get_gemini_connection_status() -> Dict[str, Any]:
    """
    Checks the active Gemini API configuration status.

    Returns:
        dict:
            - is_configured (bool): True if API key is present and valid.
            - model (str): Configured model identifier.
            - masked_key (str): Masked representation of key for display (e.g. AIza...4xY).
            - message (str): Human-friendly status text.
    """
    key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY or ""
    key = key.strip()

    if not key or key in ("", "your_key_here"):
        return {
            "is_configured": False,
            "model": GEMINI_MODEL or DEFAULT_MODEL,
            "masked_key": "None",
            "message": "API key not configured in .env",
        }

    masked = f"{key[:4]}...{key[-4:]}" if len(key) >= 10 else "******"
    return {
        "is_configured": True,
        "model": GEMINI_MODEL or DEFAULT_MODEL,
        "masked_key": masked,
        "message": f"Connected to {GEMINI_MODEL or DEFAULT_MODEL}",
    }


def process_invoice_upload(
    image_bytes: bytes,
    filename: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Processes an uploaded invoice image:
    1. Validates byte content, format extension, and file size.
    2. Inspects image integrity using Pillow.
    3. Invokes Google Gemini via extract_invoice().
    4. Cleans and standardizes extracted fields.
    5. Validates arithmetic and business rules.

    Args:
        image_bytes: Raw binary bytes of the uploaded image file.
        filename: Name of the uploaded file (used for extension detection).
        api_key: Optional API key override.
        model: Optional model name override.

    Returns:
        dict containing:
            - invoice_data: Standardized invoice dictionary with metadata.
            - validation: Complete validation result with calculated details.

    Raises:
        ImageValidationError: If image is empty, oversized, corrupt, or unsupported.
        ConfigurationError: If API key is not configured.
        APIExtractionError: If Gemini API fails.
        JSONParsingError: If valid JSON could not be decoded.
    """
    if not image_bytes or len(image_bytes) == 0:
        raise ImageValidationError("Uploaded image file is empty (0 bytes).")

    if len(image_bytes) > MAX_IMAGE_FILE_SIZE_BYTES:
        mb = len(image_bytes) / (1024 * 1024)
        raise ImageValidationError(
            f"Uploaded file exceeds maximum allowed size of 20 MB (current size: {mb:.1f} MB)."
        )

    # Validate file extension
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_MIME_TYPES:
        supported = ", ".join(SUPPORTED_MIME_TYPES.keys())
        raise ImageValidationError(
            f"Unsupported file format '{ext}'. Supported formats are: {supported}"
        )

    # Verify actual image content with Pillow
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, Exception) as err:
        raise ImageValidationError(
            f"Uploaded file '{filename}' is corrupted or not a valid image: {err}"
        ) from err

    # Write temporary file to pass to extract_invoice
    temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    temp_path = Path(temp_file.name)

    try:
        temp_file.write(image_bytes)
        temp_file.flush()
        temp_file.close()

        # Step 1: Run Gemini Multimodal AI extraction
        raw_data = extract_invoice(
            image_path=temp_path,
            api_key=api_key,
            model=model,
        )

        # Step 2: Clean and defensively standardize
        invoice_data = clean_invoice_data(raw_data)

        # Preserve metadata from extraction
        if "_metadata" in raw_data:
            invoice_data["_metadata"] = raw_data["_metadata"]

        # Step 3: Run financial arithmetic validation
        validation_result = validate_invoice(invoice_data)

        return {
            "invoice_data": invoice_data,
            "validation": validation_result,
        }

    finally:
        # Guarantee cleanup of temporary file
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def revalidate_edited_invoice(edited_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Revalidates edited invoice data from the UI without making new AI API calls.

    Performs:
    1. Defensive cleaning of modified inputs (converting numeric strings, stripping units).
    2. Complete financial validation (line totals, subtotal match, tax consistency).

    Args:
        edited_data: Modified invoice dictionary from Streamlit editor/form.

    Returns:
        dict containing:
            - invoice_data: Standardized and cleaned updated invoice data.
            - validation: Recalculated validation report with new line totals.
    """
    cleaned_data = clean_invoice_data(edited_data)

    # Preserve metadata if present
    if "_metadata" in edited_data:
        cleaned_data["_metadata"] = edited_data["_metadata"]

    validation_result = validate_invoice(cleaned_data)

    return {
        "invoice_data": cleaned_data,
        "validation": validation_result,
    }


def create_session_history_record(
    filename: str,
    invoice_data: Dict[str, Any],
    validation: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Creates a standardized session history record for tracking recent extractions.

    Args:
        filename: Name of the processed image file.
        invoice_data: Extracted invoice dictionary.
        validation: Validation report dictionary.

    Returns:
        dict: Lightweight audit record for session history.
    """
    return {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "filename": filename,
        "invoice_number": invoice_data.get("invoice_number") or "Not detected",
        "supplier_name": invoice_data.get("supplier_name") or "Not detected",
        "total_amount": invoice_data.get("total_amount"),
        "currency": invoice_data.get("currency") or "NPR",
        "is_valid": validation.get("is_valid", False),
        "errors_count": len(validation.get("errors", [])),
        "warnings_count": len(validation.get("warnings", [])),
    }

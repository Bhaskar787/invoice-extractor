"""
Extractor Module.

Extracts structured invoice information from an image using
the official Google Gemini Python SDK (google-genai).
Includes strict file and content validation, response parsing,
markdown stripping, exponential backoff retries, model fallbacks,
and defensive data cleaning.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Silence non-critical library deprecation/runtime notices
warnings.filterwarnings("ignore")

from PIL import Image, UnidentifiedImageError
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from src.config import GEMINI_MODEL, validate_config
from src.exceptions import (
    APIExtractionError,
    ImageValidationError,
    JSONParsingError,
)

# Supported image file extensions and their corresponding MIME types
SUPPORTED_MIME_TYPES: Dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

# Maximum allowed image file size in bytes (20 MB)
MAX_IMAGE_FILE_SIZE_BYTES = 20 * 1024 * 1024

# Configurable fallback Flash models
DEFAULT_FALLBACK_MODELS: List[str] = [
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.8-flash",
]

# Canonical keys expected in every structured invoice extraction
EXPECTED_INVOICE_KEYS: List[str] = [
    "invoice_number",
    "invoice_date",
    "supplier_name",
    "currency",
    "items",
    "subtotal",
    "tax_amount",
    "total_amount",
]


# Pydantic Schemas for Gemini Structured JSON Output

class LineItem(BaseModel):
    """Schema for individual line items on the invoice."""
    description: Optional[str] = Field(
        default=None,
        description="Description or title of the product or service",
    )
    quantity: Optional[float] = Field(
        default=None,
        description="Quantity of items purchased as a plain number",
    )
    unit_price: Optional[float] = Field(
        default=None,
        description="Price per single unit as a plain number",
    )


class InvoiceData(BaseModel):
    """Schema representing the complete structured invoice extraction."""
    invoice_number: Optional[str] = Field(
        default=None,
        description="Invoice reference number or identifier (e.g., RT-2024-1052)",
    )
    invoice_date: Optional[str] = Field(
        default=None,
        description="Invoice issue date standardized to YYYY-MM-DD",
    )
    supplier_name: Optional[str] = Field(
        default=None,
        description="Name of the company/vendor issuing the invoice (NOT the 'Bill To' customer)",
    )
    currency: Optional[str] = Field(
        default=None,
        description="Currency code or symbol (e.g., NPR, USD, EUR)",
    )
    items: List[LineItem] = Field(
        default_factory=list,
        description="List of line items present on the invoice",
    )
    subtotal: Optional[float] = Field(
        default=None,
        description="Pre-tax subtotal amount as a plain number",
    )
    tax_amount: Optional[float] = Field(
        default=None,
        description="Tax or VAT amount as a plain number",
    )
    total_amount: Optional[float] = Field(
        default=None,
        description="Grand total amount payable as a plain number",
    )


# Prompt Definition

EXTRACTION_PROMPT = """You are an expert invoice data extraction system.
Analyze the provided invoice image carefully and extract key invoice information into valid JSON.

Follow these strict rules:
1. Schema & Structure:
   Extract all fields according to the following structure:
   - invoice_number: The unique invoice reference code or ID.
   - invoice_date: Issue date standardized to YYYY-MM-DD (e.g., '14 October 2024' -> '2024-10-14').
   - supplier_name: The company or vendor that ISSUED the invoice (e.g., the seller/service provider usually located at the top/header). Do NOT extract the 'Bill To' or customer recipient as the supplier.
   - currency: Currency identifier (e.g., NPR, USD, EUR).
   - items: Array of line items, each with:
       * description: Item name or service description.
       * quantity: Number of units as a plain number (e.g., 50 pcs -> 50).
       * unit_price: Price per unit as a plain number (e.g., 1,250.00 -> 1250.0).
   - subtotal: Pre-tax subtotal amount as a plain number.
   - tax_amount: VAT/tax amount as a plain number.
   - total_amount: Final grand total payable as a plain number.

2. Supplier vs Bill To:
   - The supplier is the issuer of the invoice (often found in the logo, company header, or payment details).
   - Never confuse the supplier with the 'Bill To' / customer recipient.

3. Accuracy & Missing Values:
   - Use null for any field that is missing, unreadable, or not explicitly stated.
   - NEVER invent, assume, or hallucinate data.

4. Numeric Formatting:
   - All numbers (quantity, unit_price, subtotal, tax_amount, total_amount) must be pure numeric values (floats or integers).
   - Strip all commas, currency symbols, and unit labels from numeric fields.

5. Output Format:
   - Return ONLY a valid JSON object. No explanation, no Markdown formatting, and no code blocks.
"""


# Parsing and Data Cleaning Helpers

def parse_json_response(raw_text: str) -> Dict[str, Any]:
    """
    Parses a raw text reply from the model into a Python dictionary.

    If the reply contains markdown code fences (```json or ```), it strips
    them first before decoding.

    Args:
        raw_text: Raw string returned by the model.

    Returns:
        dict: Parsed JSON content as a dictionary.

    Raises:
        JSONParsingError: If raw_text is empty or cannot be parsed as a JSON object.
    """
    if not raw_text or not raw_text.strip():
        raise JSONParsingError("The AI model returned an empty response.")

    cleaned = raw_text.strip()

    # Strip markdown code fences if present (e.g., ```json\n{...}\n``` or ```\n{...}\n```)
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as err:
        snippet = raw_text[:200] + ("..." if len(raw_text) > 200 else "")
        raise JSONParsingError(
            f"Failed to decode model response as JSON: {err}\nResponse snippet:\n{snippet}"
        ) from err

    if not isinstance(data, dict):
        raise JSONParsingError(
            f"Expected JSON root to be an object (dict), but got: {type(data).__name__}"
        )

    return data


def _extract_text_from_response(response: Any) -> str:
    """Safely extracts text parts from response candidates without triggering thought_signature warnings."""
    candidates = getattr(response, "candidates", None)
    if candidates and len(candidates) > 0:
        content = getattr(candidates[0], "content", None)
        parts = getattr(content, "parts", None)
        if parts:
            text_parts = [p.text for p in parts if getattr(p, "text", None)]
            if text_parts:
                return "".join(text_parts).strip()
    return (getattr(response, "text", "") or "").strip()


def _clean_number(val: Any) -> Optional[Union[float, int]]:

    """
    Sanitizes and converts numeric values to float, int, or None.

    Strict rules:
    - Booleans are explicitly rejected (bool is subclass of int in Python).
    - None or empty string -> returns None.
    - Non-finite numbers (NaN, Inf) -> returns None.
    - Strings with currency signs and formatting are cleanly parsed.
    - Arbitrary text or malformed numeric strings (e.g. "abc123def") are REJECTED (returns None).
    """
    # Reject boolean types (bool is a subclass of int)
    if isinstance(val, bool) or val is None or val == "":
        return None

    # Validate finite float/int
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return int(val) if isinstance(val, float) and val.is_integer() else val

    if isinstance(val, str):
        text = val.strip()
        if not text:
            return None

        # Remove thousand separator commas
        cleaned = text.replace(",", "")

        # Strip recognized leading currency symbols or codes
        cleaned = re.sub(
            r"^\s*(?:NPR|USD|EUR|GBP|AUD|CAD|CHF|CNY|JPY|Rs\.?|\$|€|£|¥)\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        # Strip recognized trailing unit words
        cleaned = re.sub(
            r"\s*(?:pcs|pc|pieces|units|unit|hrs|hr|hours|hour|lot|lots|m|meter|meters|kg|kgs)\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        # Strict float conversion (rejects partial matches like "abc123")
        try:
            num = float(cleaned)
            if math.isnan(num) or math.isinf(num):
                return None
            return int(num) if num.is_integer() else num
        except ValueError:
            return None

    return None


def clean_invoice_data(data: Any) -> Dict[str, Any]:
    """
    Cleans and standardizes raw extracted invoice data.

    Improvements:
    1. Rejects non-dictionary input explicitly.
    2. Missing item descriptions remain None (preserves missing data, no placeholders).
    3. Invalid item objects are flagged rather than silently discarded.
    4. Numeric strings are strictly sanitized to finite float/int.
    5. Missing fields are preserved as None (null in JSON).

    Args:
        data: Raw extracted dictionary from JSON parsing.

    Returns:
        dict: Standardized invoice dictionary.

    Raises:
        ValueError: If data is not a dictionary.
    """
    # Reject non-dictionary input
    if not isinstance(data, dict):
        raise ValueError(
            f"clean_invoice_data expected a dictionary, but received: {type(data).__name__}"
        )

    cleaned: Dict[str, Any] = {}

    # Standardize string fields (None if missing, empty, or non-string)
    for field in ["invoice_number", "invoice_date", "supplier_name", "currency"]:
        val = data.get(field)
        if val is not None and not isinstance(val, (dict, list)):
            val_str = str(val).strip()
            cleaned[field] = val_str if val_str else None
        else:
            cleaned[field] = None

    # Standardize line items
    raw_items = data.get("items")
    cleaned_items: List[Dict[str, Any]] = []

    if isinstance(raw_items, list):
        for item in raw_items:
            # If item is not a dict, preserve it as an invalid item object
            if not isinstance(item, dict):
                cleaned_items.append(
                    {
                        "description": None,
                        "quantity": None,
                        "unit_price": None,
                        "_invalid_raw_item": item,
                    }
                )
                continue

            # Preserve missing description as None without placeholder substitution
            raw_desc = item.get("description")
            if raw_desc is not None and not isinstance(raw_desc, (dict, list)):
                desc_str = str(raw_desc).strip()
                cleaned_desc = desc_str if desc_str else None
            else:
                cleaned_desc = None

            cleaned_items.append(
                {
                    "description": cleaned_desc,
                    "quantity": _clean_number(item.get("quantity")),
                    "unit_price": _clean_number(item.get("unit_price")),
                }
            )
    elif raw_items is not None:
        # Non-list items passed; pass through so validator can flag type violation
        cleaned["items"] = raw_items
        # Clean numeric summary fields
        cleaned["subtotal"] = _clean_number(data.get("subtotal"))
        cleaned["tax_amount"] = _clean_number(data.get("tax_amount"))
        cleaned["total_amount"] = _clean_number(data.get("total_amount"))
        return cleaned

    cleaned["items"] = cleaned_items

    # Standardize monetary and summary numbers
    cleaned["subtotal"] = _clean_number(data.get("subtotal"))
    cleaned["tax_amount"] = _clean_number(data.get("tax_amount"))
    cleaned["total_amount"] = _clean_number(data.get("total_amount"))

    return cleaned


# File & Image Content Validation

def _validate_image_file(image_path: Path) -> str:
    """
    Validate that the file exists, is within reasonable size limits,
    has a supported extension, and is a valid readable image.

    Args:
        image_path: Resolved path to the target image.

    Returns:
        str: MIME type string.

    Raises:
        ImageValidationError: If file is missing, is a directory, exceeds size limit,
                              has an unsupported extension, or is corrupted.
    """
    if not image_path.exists():
        raise ImageValidationError(
            f"Invoice image file not found at: '{image_path}'.\n"
            "Please check the path and try again."
        )

    if not image_path.is_file():
        raise ImageValidationError(
            f"The path '{image_path}' points to a directory, not a file."
        )

    # Verify file size limit
    try:
        file_size = image_path.stat().st_size
    except OSError as err:
        raise ImageValidationError(f"Could not read metadata for image at '{image_path}': {err}") from err

    if file_size > MAX_IMAGE_FILE_SIZE_BYTES:
        mb = file_size / (1024 * 1024)
        raise ImageValidationError(
            f"Image file exceeds maximum allowed size of 20 MB (current size: {mb:.1f} MB)."
        )

    ext = image_path.suffix.lower()
    if ext not in SUPPORTED_MIME_TYPES:
        supported = ", ".join(SUPPORTED_MIME_TYPES.keys())
        raise ImageValidationError(
            f"Unsupported file format '{ext}'.\n"
            f"Supported image formats are: {supported}"
        )

    # Verify image integrity using Pillow
    try:
        with Image.open(image_path) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, Exception) as err:
        raise ImageValidationError(
            f"Image file at '{image_path}' is corrupted or not a valid image: {err}"
        ) from err

    return SUPPORTED_MIME_TYPES[ext]


# Main Extraction Function with Fallbacks & Backoff

def extract_invoice(
    image_path: str | Path,
    api_key: str | None = None,
    model: str | None = None,
) -> Dict[str, Any]:
    """
    Reads an invoice image and uses Google Gemini to extract structured invoice data.

    Features:
    - Pre-flight image content and size validation.
    - Structured output using Pydantic response_schema.
    - Configurable fallback model list with separate handling for 429 quota, 503 high demand, and 404.
    - Exponential backoff for temporary rate limits and demand spikes.
    - Explicit detection of blocked or truncated responses.
    - Enriched extraction metadata (model used, retries).

    Args:
        image_path: Path to the invoice image file.
        api_key: Optional Gemini API key override (defaults to config).
        model: Optional model name override (defaults to config).

    Returns:
        dict: Standardized, cleaned invoice data with metadata.

    Raises:
        ImageValidationError: If image is missing, oversized, or corrupted.
        ConfigurationError: If API key is not configured in .env.
        APIExtractionError: If Gemini API network/auth/quota requests fail.
        JSONParsingError: If valid JSON cannot be parsed after retry.
    """
    path = Path(image_path).resolve()
    mime_type = _validate_image_file(path)

    # Validate API key configuration
    resolved_api_key = validate_config(api_key)
    primary_model = model or GEMINI_MODEL

    # Read binary bytes of the image
    try:
        with open(path, "rb") as f:
            image_bytes = f.read()
    except OSError as err:
        raise ImageValidationError(f"Could not read image file at '{path}': {err}") from err

    # Initialize Gemini client
    try:
        client = genai.Client(api_key=resolved_api_key)
    except Exception as err:
        raise APIExtractionError(f"Failed to initialize Gemini client: {err}") from err

    # Prepare multimodal image part
    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type,
    )

    # Enforce structured JSON schema and zero temperature
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=InvoiceData,
        temperature=0.0,
    )

    # Configure fallback models
    env_fallbacks = os.getenv("GEMINI_FALLBACK_MODELS")
    if env_fallbacks:
        configured_fallbacks = [m.strip() for m in env_fallbacks.split(",") if m.strip()]
    else:
        configured_fallbacks = DEFAULT_FALLBACK_MODELS

    candidate_models: List[str] = [primary_model]
    for fb in configured_fallbacks:
        if fb not in candidate_models:
            candidate_models.append(fb)

    last_api_error: Optional[Exception] = None
    last_parse_error: Optional[Exception] = None

    for model_idx, active_model in enumerate(candidate_models):
        max_attempts_per_model = 2

        for attempt in range(1, max_attempts_per_model + 1):
            try:
                response = client.models.generate_content(
                    model=active_model,
                    contents=[image_part, EXTRACTION_PROMPT],
                    config=config,
                )
            except Exception as err:
                err_msg = str(err)
                last_api_error = err

                # Check status code or structured error attributes if available
                status_code = getattr(err, "code", None) or getattr(err, "status_code", None)

                # Fatal 1: Authentication failure (bad API key) cannot be solved by switching models
                if (
                    status_code == 403
                    or any(term in err_msg.lower() for term in ["api_key_invalid", "unregistered", "unauthorized"])
                ):
                    raise APIExtractionError(
                        "Authentication failed: The configured GEMINI_API_KEY is invalid or unauthorized.\n"
                        "Please verify your API key in '.env' or create a new key at https://aistudio.google.com/."
                    ) from err

                # Fatal 2: Network disconnection cannot be solved by switching models
                if any(term in err_msg.lower() for term in ["connection", "timeout", "socket", "dns", "nameresolution"]):
                    raise APIExtractionError(
                        "Network connection error: Unable to reach Google Gemini API.\n"
                        "Please check your internet connection or proxy settings."
                    ) from err

                # Handle rate limits (429) and high server load (503) with exponential backoff
                is_rate_limit = status_code == 429 or "429" in err_msg or "resource_exhausted" in err_msg.lower()
                is_server_busy = status_code == 503 or "503" in err_msg or "unavailable" in err_msg.lower()
                is_model_not_found = status_code == 404 or "404" in err_msg or "not_found" in err_msg.lower()

                if is_rate_limit or is_server_busy:
                    if attempt < max_attempts_per_model:
                        backoff_delay = min(1.5 ** attempt, 6.0)
                        print(
                            f"[Notice] Model '{active_model}' returned temporary load notice ({'Rate Limit' if is_rate_limit else 'Busy'}). "
                            f"Retrying in {backoff_delay:.1f}s (attempt {attempt}/{max_attempts_per_model})..."
                        )
                        time.sleep(backoff_delay)
                        continue

                # Model availability failure (404 deprecated or exhausted retries on busy model)
                has_next_model = (model_idx + 1) < len(candidate_models)
                if has_next_model and (is_model_not_found or is_server_busy or is_rate_limit):
                    next_model = candidate_models[model_idx + 1]
                    print(
                        f"[Notice] Model '{active_model}' unavailable. "
                        f"Automatically switching to fallback model '{next_model}'..."
                    )
                    break

                # If no more models, raise clean APIExtractionError
                raise APIExtractionError(
                    f"Google Gemini API error while processing the invoice with model '{active_model}': {err}"
                ) from err

            # Inspect finish_reason for safety filter blocks or token truncation
            candidates = getattr(response, "candidates", None)
            if candidates and len(candidates) > 0:
                first_cand = candidates[0]
                finish_reason = str(getattr(first_cand, "finish_reason", "")).upper()
                if "SAFETY" in finish_reason or "BLOCK" in finish_reason:
                    raise APIExtractionError(
                        f"Invoice processing was blocked by safety filters (finish_reason: {finish_reason})."
                    )
                if "MAX_TOKENS" in finish_reason:
                    raise APIExtractionError(
                        "Invoice extraction was truncated because maximum output token limit was reached."
                    )

            # Process the response
            try:

                # 1. Check if SDK already populated response.parsed
                if hasattr(response, "parsed") and response.parsed is not None:
                    if isinstance(response.parsed, BaseModel):
                        raw_dict = response.parsed.model_dump()
                    elif isinstance(response.parsed, dict):
                        raw_dict = response.parsed
                    else:
                        raw_text = _extract_text_from_response(response)
                        raw_dict = parse_json_response(raw_text)
                else:
                    raw_text = _extract_text_from_response(response)
                    raw_dict = parse_json_response(raw_text)

                cleaned_data = clean_invoice_data(raw_dict)


                # Include extraction metadata
                cleaned_data["_metadata"] = {
                    "model_used": active_model,
                    "model_fallback_applied": active_model != primary_model,
                    "attempt": attempt,
                    "image_size_bytes": len(image_bytes),
                    "mime_type": mime_type,
                }
                return cleaned_data

            except JSONParsingError as parse_err:
                last_parse_error = parse_err
                if attempt < max_attempts_per_model:
                    print(
                        f"[Notice] Model response parsing failed on attempt {attempt}/{max_attempts_per_model}. "
                        "Retrying extraction..."
                    )
                    continue
                if (model_idx + 1) < len(candidate_models):
                    next_model = candidate_models[model_idx + 1]
                    print(
                        f"[Notice] Model '{active_model}' failed JSON decoding after retries. "
                        f"Trying fallback model '{next_model}'..."
                    )
                    break
                raise JSONParsingError(
                    f"Failed to obtain valid JSON from Gemini after {max_attempts_per_model} attempts.\n"
                    f"Reason: {last_parse_error}"
                ) from last_parse_error

    if last_api_error:
        raise APIExtractionError(f"All candidate Gemini models failed: {last_api_error}")
    raise JSONParsingError(f"Invoice extraction failed: {last_parse_error}")

"""
Unit Tests for Extractor Module.

Tests numeric sanitization, defensive data cleaning, image validation,
API failure modes, retry/fallback mechanisms, and end-to-end extraction pipeline
using mocked Gemini responses (no paid API calls required).
"""

from __future__ import annotations

import io
import json
import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from src.config import validate_config
from src.exceptions import (
    APIExtractionError,
    ConfigurationError,
    ImageValidationError,
    JSONParsingError,
)
from src.extractor import (
    _clean_number,
    _validate_image_file,
    clean_invoice_data,
    extract_invoice,
    parse_json_response,
)


# 1. Numeric Sanitization Tests (_clean_number)

def test_clean_number_finite_floats_and_integers() -> None:
    """Verify clean_number handles standard integers and floats correctly."""
    assert _clean_number(50) == 50
    assert _clean_number(1250.5) == 1250.5
    assert _clean_number(100.0) == 100


def test_clean_number_rejects_booleans() -> None:
    """In Python bool is subclass of int; reject True and False."""
    assert _clean_number(True) is None
    assert _clean_number(False) is None


def test_clean_number_rejects_nan_and_infinity() -> None:
    """Reject non-finite numbers (NaN, Inf, -Inf)."""
    assert _clean_number(float("nan")) is None
    assert _clean_number(float("inf")) is None
    assert _clean_number(float("-inf")) is None


def test_clean_number_parses_formatted_currency_strings() -> None:
    """Verify clean_number strips commas and recognized currency symbols."""
    assert _clean_number("$1,250.00") == 1250.0
    assert _clean_number("NPR 100,500") == 100500
    assert _clean_number("€99.99") == 99.99
    assert _clean_number("£450.50") == 450.5
    assert _clean_number("Rs. 1,500.00") == 1500
    assert _clean_number("¥5000") == 5000


def test_clean_number_parses_trailing_unit_words() -> None:
    """Verify clean_number strips trailing quantity or service unit labels."""
    assert _clean_number("50 pcs") == 50
    assert _clean_number("20 units") == 20
    assert _clean_number("10 hours") == 10
    assert _clean_number("6 m") == 6
    assert _clean_number("100 kg") == 100


def test_clean_number_rejects_malformed_numeric_strings() -> None:
    """Reject ambiguous or malformed numeric strings."""
    assert _clean_number("abc123def") is None
    assert _clean_number("123abc") is None
    assert _clean_number("invoice123") is None
    assert _clean_number("foo") is None
    assert _clean_number("$") is None
    assert _clean_number("") is None
    assert _clean_number(None) is None


# 2. Defensive Data Cleaning Tests (clean_invoice_data)

def test_clean_invoice_data_rejects_non_dictionary() -> None:
    """Rejects non-dictionary input explicitly."""
    with pytest.raises(ValueError, match="clean_invoice_data expected a dictionary"):
        clean_invoice_data("not a dictionary")

    with pytest.raises(ValueError):
        clean_invoice_data([1, 2, 3])


def test_clean_invoice_data_preserves_missing_item_description_as_none() -> None:
    """Missing item description remains None without placeholder."""
    raw = {
        "invoice_number": "RT-2024-1052",
        "items": [
            {"description": None, "quantity": 10, "unit_price": 50.0},
            {"description": "", "quantity": 5, "unit_price": 20.0},
        ],
    }
    cleaned = clean_invoice_data(raw)
    assert cleaned["items"][0]["description"] is None
    assert cleaned["items"][1]["description"] is None


def test_clean_invoice_data_preserves_invalid_item_objects() -> None:
    """Non-dictionary item objects preserved for validator to catch."""
    raw = {
        "items": [
            "corrupted_item_string",
            {"description": "Valid Item", "quantity": 1, "unit_price": 100.0},
        ],
    }
    cleaned = clean_invoice_data(raw)
    assert len(cleaned["items"]) == 2
    assert "_invalid_raw_item" in cleaned["items"][0]
    assert cleaned["items"][1]["description"] == "Valid Item"


def test_clean_invoice_data_passes_through_non_list_items() -> None:
    """Passes through non-list items to trigger validator error."""
    raw = {
        "items": "should_be_a_list",
        "total_amount": "100.00",
    }
    cleaned = clean_invoice_data(raw)
    assert cleaned["items"] == "should_be_a_list"
    assert cleaned["total_amount"] == 100.0


# 3. File & Image Validation Tests (_validate_image_file)

def test_image_validation_missing_file_raises_error(tmp_path: Path) -> None:
    """Missing image file raises ImageValidationError."""
    missing = tmp_path / "nonexistent.png"
    with pytest.raises(ImageValidationError, match="not found"):
        _validate_image_file(missing)


def test_image_validation_directory_path_raises_error(tmp_path: Path) -> None:
    """Path pointing to a directory raises ImageValidationError."""
    with pytest.raises(ImageValidationError, match="points to a directory"):
        _validate_image_file(tmp_path)


def test_image_validation_unsupported_format_raises_error(tmp_path: Path) -> None:
    """Unsupported file extension raises ImageValidationError."""
    text_file = tmp_path / "invoice.txt"
    text_file.write_text("dummy invoice text")
    with pytest.raises(ImageValidationError, match="Unsupported file format"):
        _validate_image_file(text_file)


def test_image_validation_corrupted_image_raises_error(tmp_path: Path) -> None:
    """Non-image byte file with .png extension raises ImageValidationError."""
    corrupted = tmp_path / "corrupted.png"
    corrupted.write_bytes(b"NOT_A_VALID_PNG_FILE_DATA_CORRUPTED")
    with pytest.raises(ImageValidationError, match="corrupted or not a valid image"):
        _validate_image_file(corrupted)


def test_image_validation_oversized_file_raises_error(tmp_path: Path) -> None:
    """File exceeding 20 MB size limit raises ImageValidationError."""
    oversized = tmp_path / "huge.png"
    oversized.write_bytes(b"0" * 10)
    real_stat = oversized.stat()
    with patch.object(Path, "stat") as mock_stat:
        mock_stat_res = MagicMock()
        mock_stat_res.st_size = 25 * 1024 * 1024  # 25 MB
        mock_stat_res.st_mode = real_stat.st_mode
        mock_stat.return_value = mock_stat_res
        with pytest.raises(ImageValidationError, match="exceeds maximum allowed size of 20 MB"):
            _validate_image_file(oversized)



def test_image_validation_valid_png_succeeds(tmp_path: Path) -> None:
    """Valid small PNG image passes validation and returns correct MIME type."""
    valid_img = tmp_path / "valid.png"
    img = Image.new("RGB", (10, 10), color="blue")
    img.save(valid_img, format="PNG")

    mime = _validate_image_file(valid_img)
    assert mime == "image/png"


# 4. Configuration Validation Tests (validate_config)

def test_validate_config_missing_or_placeholder_raises_error() -> None:
    """Missing or placeholder API key raises ConfigurationError."""
    with pytest.raises(ConfigurationError, match="GEMINI_API_KEY is missing or invalid"):
        validate_config("")

    with pytest.raises(ConfigurationError):
        validate_config("your_key_here")


def test_validate_config_valid_key_returns_key() -> None:
    """Valid non-empty API key is accepted."""
    assert validate_config("AIzaSyDUMMYKEY1234567890") == "AIzaSyDUMMYKEY1234567890"


# 5. Model JSON Response Parsing Tests (parse_json_response)

def test_parse_json_response_with_markdown_code_fences() -> None:
    """Markdown ```json ... ``` blocks are cleanly stripped."""
    payload = {"invoice_number": "INV-100", "total_amount": 500.0}
    raw = f"```json\n{json.dumps(payload)}\n```"
    result = parse_json_response(raw)
    assert result["invoice_number"] == "INV-100"
    assert result["total_amount"] == 500.0


def test_parse_json_response_empty_raises_error() -> None:
    """Empty or whitespace response raises JSONParsingError."""
    with pytest.raises(JSONParsingError, match="returned an empty response"):
        parse_json_response("")
    with pytest.raises(JSONParsingError, match="returned an empty response"):
        parse_json_response("   \n\t  ")


def test_parse_json_response_malformed_raises_error() -> None:
    """Non-JSON raw text raises JSONParsingError."""
    with pytest.raises(JSONParsingError, match="Failed to decode model response as JSON"):
        parse_json_response("This is not a JSON object: {unclosed")


# 6. Gemini API Interaction, Retries, Fallback & Pipeline (extract_invoice)

@pytest.fixture
def dummy_png(tmp_path: Path) -> Path:
    """Creates a temporary valid PNG file."""
    path = tmp_path / "test_invoice.png"
    img = Image.new("RGB", (20, 20), color="white")
    img.save(path, format="PNG")
    return path


def test_extract_invoice_fatal_auth_error_no_fallback(dummy_png: Path) -> None:
    """403 / invalid API key raises immediately without cycling fallbacks."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("403 Forbidden: API_KEY_INVALID")

    with patch("src.extractor.genai.Client", return_value=mock_client):
        with pytest.raises(APIExtractionError, match="Authentication failed"):
            extract_invoice(dummy_png, api_key="dummy_invalid_key")


def test_extract_invoice_rate_limit_exponential_backoff(dummy_png: Path) -> None:
    """429 triggers exponential backoff retry on same model."""
    valid_payload = {
        "invoice_number": "RT-2024-1052",
        "invoice_date": "2024-10-14",
        "supplier_name": "Rivertech Supplies Ltd.",
        "currency": "NPR",
        "items": [
            {"description": "HDPE Pipe", "quantity": 10, "unit_price": 500.0}
        ],
        "subtotal": 5000.0,
        "tax_amount": 650.0,
        "total_amount": 5650.0,
    }

    mock_resp = MagicMock()
    mock_resp.candidates = [MagicMock(finish_reason="STOP")]
    mock_resp.parsed = None
    mock_resp.text = json.dumps(valid_payload)

    # First attempt raises 429, second attempt succeeds
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        Exception("429 Resource Exhausted / Rate limit"),
        mock_resp,
    ]

    with patch("src.extractor.genai.Client", return_value=mock_client):
        with patch("src.extractor.time.sleep") as mock_sleep:
            result = extract_invoice(dummy_png, api_key="dummy_key", model="gemini-3-flash-preview")
            assert result["invoice_number"] == "RT-2024-1052"
            assert result["_metadata"]["attempt"] == 2
            assert mock_sleep.called


def test_extract_invoice_model_fallback_on_404(dummy_png: Path) -> None:
    """404 (model not found/deprecated) triggers fallback to next model."""
    valid_payload = {
        "invoice_number": "INV-FALLBACK-1",
        "invoice_date": "2024-10-14",
        "supplier_name": "Rivertech Supplies Ltd.",
        "currency": "NPR",
        "items": [{"description": "Pipe", "quantity": 1, "unit_price": 100.0}],
        "subtotal": 100.0,
        "tax_amount": 13.0,
        "total_amount": 113.0,
    }

    mock_resp = MagicMock()
    mock_resp.candidates = [MagicMock(finish_reason="STOP")]
    mock_resp.parsed = None
    mock_resp.text = json.dumps(valid_payload)

    # Primary model raises 404 NOT_FOUND, fallback succeeds
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        Exception("404 NOT_FOUND: Model models/gemini-2.5-flash is no longer available"),
        mock_resp,
    ]

    with patch("src.extractor.genai.Client", return_value=mock_client):
        result = extract_invoice(
            dummy_png,
            api_key="dummy_key",
            model="gemini-2.5-flash",
        )
        assert result["invoice_number"] == "INV-FALLBACK-1"
        assert result["_metadata"]["model_fallback_applied"] is True


def test_extract_invoice_blocked_by_safety_filter(dummy_png: Path) -> None:
    """Blocked by safety filter candidate raises APIExtractionError."""
    mock_resp = MagicMock()
    mock_cand = MagicMock()
    mock_cand.finish_reason = "SAFETY"
    mock_resp.candidates = [mock_cand]

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with patch("src.extractor.genai.Client", return_value=mock_client):
        with pytest.raises(APIExtractionError, match="blocked by safety filters"):
            extract_invoice(dummy_png, api_key="dummy_key")


def test_extract_invoice_complete_pipeline(dummy_png: Path) -> None:
    """End-to-end extraction pipeline verification."""
    invoice_payload = {
        "invoice_number": "RT-2024-1052",
        "invoice_date": "2024-10-14",
        "supplier_name": "Rivertech Supplies Ltd.",
        "currency": "NPR",
        "items": [
            {"description": "HDPE Pipe 110mm", "quantity": "50 pcs", "unit_price": "Rs. 1,250.00"},
            {"description": "Delivery Charge", "quantity": 1, "unit_price": "$5,000.00"},
        ],
        "subtotal": "67,500.00",
        "tax_amount": "8,775.00",
        "total_amount": "76,275.00",
    }

    mock_resp = MagicMock()
    mock_resp.candidates = [MagicMock(finish_reason="STOP")]
    mock_resp.parsed = None
    mock_resp.text = json.dumps(invoice_payload)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp

    with patch("src.extractor.genai.Client", return_value=mock_client):
        data = extract_invoice(dummy_png, api_key="dummy_key")

        # Verify cleaning
        assert data["invoice_number"] == "RT-2024-1052"
        assert data["items"][0]["quantity"] == 50
        assert data["items"][0]["unit_price"] == 1250.0
        assert data["items"][1]["unit_price"] == 5000.0
        assert data["subtotal"] == 67500.0
        assert data["total_amount"] == 76275.0

        # Verify metadata
        assert "_metadata" in data
        assert "model_used" in data["_metadata"]
        assert data["_metadata"]["image_size_bytes"] > 0

"""
Unit and integration tests for src/services.py.
"""

from io import BytesIO
from unittest.mock import MagicMock, patch
from PIL import Image
import pytest

from src.exceptions import ImageValidationError
from src.services import (
    create_session_history_record,
    get_gemini_connection_status,
    process_invoice_upload,
    revalidate_edited_invoice,
)


@pytest.fixture
def valid_png_bytes() -> bytes:
    """Generates 1x1 valid PNG in bytes."""
    buf = BytesIO()
    img = Image.new("RGB", (10, 10), color="white")
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestGetGeminiConnectionStatus:
    """Tests for get_gemini_connection_status."""

    def test_configured_status(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyD1234567890abcdef")
        status = get_gemini_connection_status()
        assert status["is_configured"] is True
        assert status["masked_key"] == "AIza...cdef"
        assert "Connected to" in status["message"]

    def test_unconfigured_empty_status(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setattr("src.services.GEMINI_API_KEY", "")
        status = get_gemini_connection_status()
        assert status["is_configured"] is False
        assert status["masked_key"] == "None"

    def test_unconfigured_placeholder_status(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "your_key_here")
        monkeypatch.setattr("src.services.GEMINI_API_KEY", "your_key_here")
        status = get_gemini_connection_status()
        assert status["is_configured"] is False


class TestProcessInvoiceUpload:
    """Tests for process_invoice_upload."""

    def test_empty_bytes_raises(self):
        with pytest.raises(ImageValidationError, match="empty"):
            process_invoice_upload(b"", "invoice.png")

    def test_oversized_file_raises(self):
        oversized = b"0" * (20 * 1024 * 1024 + 1)
        with pytest.raises(ImageValidationError, match="exceeds maximum allowed size"):
            process_invoice_upload(oversized, "invoice.png")

    def test_unsupported_format_raises(self, valid_png_bytes):
        with pytest.raises(ImageValidationError, match="Unsupported file format"):
            process_invoice_upload(valid_png_bytes, "invoice.exe")

    def test_corrupted_image_bytes_raises(self):
        corrupt_bytes = b"NOT_A_VALID_IMAGE_DATA_12345"
        with pytest.raises(ImageValidationError, match="corrupted or not a valid image"):
            process_invoice_upload(corrupt_bytes, "invoice.png")

    @patch("src.services.extract_invoice")
    def test_successful_processing_pipeline(self, mock_extract, valid_png_bytes):
        mock_extract.return_value = {
            "supplier_name": "Rivertech Supplies Ltd.",
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-03-24",
            "currency": "NPR",
            "items": [
                {
                    "description": "Widget A",
                    "quantity": 2,
                    "unit_price": 50.0,
                }
            ],
            "subtotal": 100.0,
            "tax_amount": 13.0,
            "total_amount": 113.0,
        }

        result = process_invoice_upload(valid_png_bytes, "test_invoice.png")

        assert "invoice_data" in result
        assert "validation" in result
        assert result["invoice_data"]["supplier_name"] == "Rivertech Supplies Ltd."
        assert result["validation"]["is_valid"] is True
        assert result["validation"]["calculated_details"]["calculated_items_sum"] == 100.0


class TestRevalidateEditedInvoice:
    """Tests for revalidate_edited_invoice offline engine."""

    def test_revalidation_with_valid_edits(self):
        edited_data = {
            "supplier_name": "Edited Supplier",
            "invoice_number": "INV-EDIT-123",
            "invoice_date": "2024-05-10",
            "currency": "NPR",
            "items": [
                {"description": "Item 1", "quantity": 3, "unit_price": 20.0},
                {"description": "Item 2", "quantity": 1, "unit_price": 40.0},
            ],
            "subtotal": 100.0,
            "tax_amount": 10.0,
            "total_amount": 110.0,
        }

        res = revalidate_edited_invoice(edited_data)
        assert res["validation"]["is_valid"] is True
        assert res["validation"]["errors"] == []
        assert res["invoice_data"]["subtotal"] == 100.0
        assert res["validation"]["calculated_details"]["calculated_items_sum"] == 100.0

    def test_revalidation_detects_arithmetic_discrepancy(self):
        edited_data = {
            "supplier_name": "Edited Supplier",
            "invoice_number": "INV-EDIT-123",
            "invoice_date": "2024-05-10",
            "currency": "NPR",
            "items": [
                {"description": "Item 1", "quantity": 3, "unit_price": 20.0},  # total 60
            ],
            "subtotal": 100.0,  # discrepancy: items sum is 60, subtotal is 100
            "tax_amount": 0.0,
            "total_amount": 100.0,
        }

        res = revalidate_edited_invoice(edited_data)
        assert res["validation"]["is_valid"] is False
        assert any("Calculated items sum" in e for e in res["validation"]["errors"])


class TestCreateSessionHistoryRecord:
    """Tests for create_session_history_record."""

    def test_record_generation(self):
        inv_data = {
            "invoice_number": "INV-999",
            "supplier_name": "Acme Inc",
            "total_amount": 500.0,
            "currency": "USD",
        }
        val = {
            "is_valid": True,
            "errors": [],
            "warnings": ["Warning 1"],
        }
        rec = create_session_history_record("doc.png", inv_data, val)

        assert rec["filename"] == "doc.png"
        assert rec["invoice_number"] == "INV-999"
        assert rec["supplier_name"] == "Acme Inc"
        assert rec["total_amount"] == 500.0
        assert rec["currency"] == "USD"
        assert rec["is_valid"] is True
        assert rec["errors_count"] == 0
        assert rec["warnings_count"] == 1
        assert "id" in rec
        assert "timestamp" in rec

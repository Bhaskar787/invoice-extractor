"""
Unit and Integration Tests for CLI Execution (main.py).

Verifies command-line interface arguments, output generation (output/result.json),
user-friendly error messages (no raw Python tracebacks), and exit codes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from main import main
from src.exceptions import APIExtractionError, ConfigurationError



@pytest.fixture
def sample_png(tmp_path: Path) -> Path:
    """Creates a temporary valid PNG image."""
    path = tmp_path / "sample_invoice.png"
    img = Image.new("RGB", (20, 20), color="white")
    img.save(path, format="PNG")
    return path


def test_cli_no_arguments_shows_usage_and_exits_1(capsys: pytest.CaptureFixture) -> None:
    """Running CLI with no arguments must display usage instructions and exit code 1."""
    with patch.object(sys, "argv", ["main.py"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower() or "usage:" in captured.err.lower()


def test_cli_missing_image_file_exits_1_with_friendly_error(capsys: pytest.CaptureFixture) -> None:
    """Running CLI with nonexistent image file path displays clean error without traceback."""
    with patch.object(sys, "argv", ["main.py", "nonexistent_invoice.png"]):
        with patch("main.validate_config", return_value="dummy_key"):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "[Error: Invalid Image]" in captured.err
    assert "Traceback" not in captured.err


def test_cli_missing_config_exits_1_with_friendly_error(capsys: pytest.CaptureFixture) -> None:
    """Running CLI when GEMINI_API_KEY is missing displays clean error without traceback."""
    with patch.object(sys, "argv", ["main.py", "dummy_image.png"]):
        with patch("main.validate_config", side_effect=ConfigurationError("GEMINI_API_KEY is missing or invalid.")):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "[Error: Configuration]" in captured.err
    assert "GEMINI_API_KEY is missing" in captured.err
    assert "Traceback" not in captured.err



def test_cli_successful_extraction_creates_output_json_and_summary(
    sample_png: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """
    Simulates a successful extraction pipeline in main.py:
    - Validates configuration
    - Calls extractor (mocked)
    - Validates business rules
    - Formats output JSON
    - Writes to output/result.json
    - Prints EXECUTION SUMMARY with exit code 0
    """
    mock_extracted_data = {
        "invoice_number": "RT-2024-1052",
        "invoice_date": "2024-10-14",
        "supplier_name": "Rivertech Supplies Ltd.",
        "currency": "NPR",
        "items": [
            {
                "description": "HDPE Pipe 110mm",
                "quantity": 50,
                "unit_price": 1250.0,
            }
        ],
        "subtotal": 62500.0,
        "tax_amount": 8125.0,
        "total_amount": 70625.0,
    }

    with patch.object(sys, "argv", ["main.py", str(sample_png)]):
        with patch("main.validate_config", return_value="dummy_api_key"):
            with patch("main.extract_invoice", return_value=mock_extracted_data):
                main()

    captured = capsys.readouterr()

    # Verify JSON output printed to stdout
    assert "invoice_data" in captured.out
    assert "RT-2024-1052" in captured.out
    assert "validation" in captured.out
    assert "EXECUTION SUMMARY" in captured.out
    assert "Invoice Status : VALID" in captured.out
    assert "Errors Count   : 0" in captured.out

    # Verify result file was written
    output_file = Path("output/result.json")
    assert output_file.exists()
    with open(output_file, "r", encoding="utf-8") as f:
        saved_json = json.load(f)
    assert saved_json["invoice_data"]["invoice_number"] == "RT-2024-1052"
    assert saved_json["validation"]["is_valid"] is True


def test_cli_api_error_suppresses_traceback_and_exits_1(
    sample_png: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    """When an API error occurs, CLI prints clean [Error: Gemini API] and exits 1."""
    with patch.object(sys, "argv", ["main.py", str(sample_png)]):
        with patch("main.validate_config", return_value="dummy_api_key"):
            with patch(
                "main.extract_invoice",
                side_effect=APIExtractionError("Connection to Gemini failed after retries."),
            ):
                with pytest.raises(SystemExit) as exc:
                    main()
                assert exc.value.code == 1

    captured = capsys.readouterr()
    assert "[Error: Gemini API]" in captured.err
    assert "Connection to Gemini failed" in captured.err
    assert "Traceback" not in captured.err

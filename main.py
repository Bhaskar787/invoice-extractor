"""
Main CLI Application.

Usage:
    python main.py <path_to_invoice_image>
    python main.py samples/invoice.png

Pipeline:
1. Parse CLI arguments (show help if no argument provided).
2. Load and validate environment configuration.
3. Extract structured invoice data from the image using Google Gemini.
4. Clean and standardize fields.
5. Validate calculations and business rules.
6. Print formatted JSON to the console.
7. Save the final payload to output/result.json.
8. Print a concise validation summary.
"""

from __future__ import annotations

import warnings
warnings.simplefilter("ignore")

import argparse
import json
import logging
import sys
from pathlib import Path

logging.getLogger("google").setLevel(logging.ERROR)
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google_genai.types").setLevel(logging.ERROR)



try:
    from src.config import validate_config
    from src.exceptions import (
        APIExtractionError,
        ConfigurationError,
        ImageValidationError,
        InvoiceExtractorError,
        JSONParsingError,
    )
    from src.extractor import clean_invoice_data, extract_invoice
    from src.validator import validate_invoice
except ImportError as err:
    print(
        f"\n[Error: Missing Dependencies] {err}\n"
        "Please install the required dependencies before running the application:\n"
        "    pip install -r requirements.txt\n",
        file=sys.stderr,
    )
    sys.exit(1)


def _build_parser() -> argparse.ArgumentParser:
    """Constructs the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="AI-Powered Invoice Data Extractor using Google Gemini.",
        usage="python main.py <path_to_invoice_image>",
    )
    parser.add_argument(
        "image_path",
        nargs="?",
        default=None,
        help="Path to the invoice image file (PNG, JPG, JPEG, WEBP).",
    )
    return parser


def main() -> None:
    """Main CLI execution routine."""
    parser = _build_parser()
    args = parser.parse_args()

    # If no argument is provided, display usage help and exit
    if not args.image_path:
        parser.print_help()
        sys.exit(1)

    image_path = Path(args.image_path)

    try:
        # Step 1: Load and validate configuration
        validate_config()

        # Step 2: Extract invoice data from the image via Google Gemini
        raw_data = extract_invoice(image_path)

        # Step 3: Clean and standardize data
        invoice_data = clean_invoice_data(raw_data)

        # Step 4: Validate business rules and calculations
        validation_result = validate_invoice(invoice_data)

        # Step 5: Construct final output schema
        final_payload = {
            "invoice_data": invoice_data,
            "validation": validation_result,
        }

        # Step 6: Print readable JSON to the console
        formatted_json = json.dumps(final_payload, indent=2, ensure_ascii=False)
        print(formatted_json)

        # Step 7: Save to output/result.json
        output_dir = Path(__file__).resolve().parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        result_file = output_dir / "result.json"

        with open(result_file, "w", encoding="utf-8") as f:
            f.write(formatted_json + "\n")

        # Step 8: Print short summary at the end
        status_label = "VALID" if validation_result["is_valid"] else "INVALID"
        num_errors = len(validation_result.get("errors", []))
        num_warnings = len(validation_result.get("warnings", []))

        print("\n" + "=" * 45)
        print("              EXECUTION SUMMARY")
        print("=" * 45)
        print(f"  Invoice Status : {status_label}")
        print(f"  Errors Count   : {num_errors}")
        print(f"  Warnings Count : {num_warnings}")
        print(f"  Saved JSON     : {result_file}")
        print("=" * 45 + "\n")

    except ImageValidationError as err:
        print(f"\n[Error: Invalid Image] {err}\n", file=sys.stderr)
        sys.exit(1)

    except ConfigurationError as err:
        print(f"\n[Error: Configuration] {err}\n", file=sys.stderr)
        sys.exit(1)

    except APIExtractionError as err:
        print(f"\n[Error: Gemini API] {err}\n", file=sys.stderr)
        sys.exit(1)

    except JSONParsingError as err:
        print(f"\n[Error: Data Parsing] {err}\n", file=sys.stderr)
        sys.exit(1)

    except InvoiceExtractorError as err:
        print(f"\n[Error] {err}\n", file=sys.stderr)
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n[Aborted] Operation cancelled by user.\n", file=sys.stderr)
        sys.exit(130)

    except Exception as err:
        print(
            f"\n[Unexpected Error] An unexpected error occurred: {err}\n",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

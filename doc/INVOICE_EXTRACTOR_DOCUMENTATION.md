# AI-Powered Invoice Data Extractor: Complete System & Architecture Documentation

---

## 1. Task Overview

### What this project does
This project is an automated Python application built to solve a real-world document processing challenge: **reading an invoice image, extracting all key data using Google Gemini's multimodal vision model, validating financial arithmetic and business integrity rules, enabling interactive corrections in a modern web UI, and exporting the verified result as structured JSON.**

### Dual Operating Modes:
1. **Interactive Streamlit Web Application (`app.py`)**: A modern, interactive web portal featuring drag-and-drop file upload, live zoom image preview, structured metadata cards, inline editable items table (`st.data_editor`), **100% offline live revalidation with zero AI calls**, granular checks audit, and one-click JSON file downloads.
2. **Command-Line Interface (`main.py`)**: A fast, scriptable CLI tool for automated pipelines, server environments, and terminal workflows.

### The Core Requirements
1. **Multimodal Extraction**: Read invoice images (`.png`, `.jpg`, `.jpeg`, `.webp`) directly without fragile OCR preprocessing.
2. **Key Field Groups**: Extract:
   - Invoice Number
   - Invoice Date (standardized to `YYYY-MM-DD`)
   - Supplier Name (the issuing company, distinguished from the "Bill To" customer)
   - Line Items list (description, quantity, unit price)
   - Total Amount (along with currency, subtotal, and tax amount)
3. **Structured Output**: Produce clean, schema-compliant JSON adhering to a defined Pydantic schema with attached execution metadata.
4. **Validation Logic**: Independently recalculate item line totals ($\text{quantity} \times \text{unit price}$), verify that the sum of line items matches the subtotal, and check that subtotal + tax matches the total amount within a $0.05$ tolerance.
5. **Strict Data Integrity**: Fail-fast on invalid financial data (missing quantities, missing unit prices, negative amounts, NaNs, infinities, booleans) while gracefully providing informative warnings for omitted optional fields (e.g. tax-exempt invoices).
6. **Interactive Correction & Offline Revalidation**: Allow users to edit detected fields and line items, rerun validation locally without consuming API credits, and download updated results.
7. **Resilience & Error Handling**: Intercept all system errors (missing files, invalid formats, unconfigured API keys, model rate limits) with clear, human-friendly messages and **zero unhandled Python stack traces**.
8. **Zero Secrets in Code**: Safely load API credentials from a `.env` file via `python-dotenv`.

---

## 2. Complete File Structure

Below is the directory layout of the application:

```text
invoice-extractor/
├── app.py                      # Interactive Streamlit Web Application entry point
├── main.py                     # Primary CLI application and end-to-end coordinator
├── components/                 # Streamlit UI presentation components
│   ├── __init__.py             # Component package exports
│   ├── header.py               # Application branding and live Gemini API connection badge
│   ├── sidebar.py              # Navigation menu, session metrics, and session reset
│   ├── uploader.py             # Drag-and-drop file uploader and extraction action controls
│   ├── invoice_preview.py      # Responsive invoice image preview with zoom inspection
│   ├── invoice_details.py      # High-level metadata cards (supplier, invoice #, date, totals)
│   ├── invoice_items.py        # Line items table and interactive editor with live revalidation
│   ├── validation_panel.py     # Overall status banner, granular rule audit, and reconciliation
│   └── json_export.py          # Syntax-highlighted JSON viewer and one-click download
├── src/                        # Core backend package (Single Source of Truth)
│   ├── __init__.py             # Package marker and runtime warning filters
│   ├── config.py               # Environment configuration and API key validation
│   ├── exceptions.py           # Custom exception classes for user-friendly error handling
│   ├── extractor.py            # Gemini vision model interaction, parsing, cleaning & retries
│   ├── validator.py            # Independent financial math and business rule validator
│   ├── services.py             # Service layer coordinating UI with extractor & validator
│   └── utils.py                # Formatting helpers, Decimal math, and DataFrame builders
├── samples/                    # Directory for input invoice images
│   └── invoice.png             # Sample invoice image (Rivertech Supplies Ltd.)
├── output/                     # Destination for generated extraction artifacts
│   └── result.json             # Final extracted JSON and validation report (CLI)
├── tests/                      # Automated test suite (85 offline tests)
│   ├── test_cli.py             # CLI argument, output generation, and error boundary tests (5 tests)
│   ├── test_extractor.py       # Number sanitization, cleaning, image validation & API (26 tests)
│   ├── test_validator.py       # Financial arithmetic, required fields, and edge-case tests (25 tests)
│   ├── test_services.py        # Connection status, upload handling, and offline revalidation (12 tests)
│   └── test_utils.py           # Currency formatting, quantities, decimal math, and JSON export (17 tests)
├── doc/                        # Project documentation directory
│   └── INVOICE_EXTRACTOR_DOCUMENTATION.md   # Complete system architecture documentation (Markdown)
├── .env.example                # Safe environment variable template
├── .gitignore                  # Prevents committing secrets, venv, and cache files
├── pytest.ini                  # Pytest configuration (sets module import path)
├── requirements.txt            # Python dependencies (Streamlit, Pandas, Pillow, google-genai)
└── README.md                   # Quickstart guide and run instructions
```

---

## 3. How the Files Relate to Each Other

The project is designed following the **Separation of Concerns (SoC)** and **Single Source of Truth (SSOT)** architectural principles:

```text
       +-----------------------+              +-----------------------+
       |        app.py         |              |        main.py        |
       |  (Streamlit Web UI)   |              |    (CLI Pipeline)     |
       +-----------+-----------+              +-----------+-----------+
                   |                                      |
                   | (delegates)                          | (coordinates)
                   v                                      v
       +-----------------------+                          |
       |    src/services.py    | <------------------------+
       |   (Orchestration &    |
       |  Offline Revalidation)|
       +-----------+-----------+
                   |
       +-----------+--------------------------------------+
       |                                                  |
       v                                                  v
+--------------+   +---------------+   +---------------+  |
|  config.py   |   |  extractor.py |   | validator.py  |  |
| (Credentials)|   | (Gemini Vision|   | (Math Auditing|  |
+-------+------+   |  & Sanitizer) |   |  & Integrity) |  |
        |          +-------+-------+   +-------+-------+  |
        |                  |                   |          |
        +--------+---------+                   |          |
                 |                             |          |
                 v                             v          v
         +---------------+             +-----------------------+
         | exceptions.py |             |       src/utils.py    |
         | (Domain Errors|             | (Currency & DataFrames|
         +---------------+             +-----------------------+
                                                   |
                                                   v
                                       +-----------------------+
                                       |        tests/         |
                                       |    85 Unit Tests      |
                                       +-----------------------+
```

### Dependency Flow Breakdown
1. **The Core Engine (`src/`) is the Single Source of Truth**: Neither the CLI (`main.py`) nor the Web App (`app.py` / `components/`) contains duplicate financial math or data extraction logic.
2. **`src/services.py` acts as the service coordinator**:
   - Pre-validates uploaded byte buffers (file size $\le 20\text{ MB}$, format extension, Pillow image verification).
   - Coordinates extraction via `extract_invoice()` and validation via `validate_invoice()`.
   - Executes **`revalidate_edited_invoice()`**: allows user edits to be cleaned and verified **100% offline with zero AI calls**.
3. **`src/utils.py` handles formatting and conversions**:
   - `format_currency()`: Generates professional currency strings (e.g. `NPR 113,565.00`) and guards against `NaN` or `None`.
   - `format_quantity()`: Formats quantities cleanly, omitting `.0` on whole numbers (`50` vs `12.5`).
   - `calculate_item_line_total()`: Accurate Decimal arithmetic with `ROUND_HALF_UP`.
   - `build_items_dataframe()`: Builds formatted pandas DataFrames for clean tabular UI display.
   - `generate_export_payload()`: Serializes standardized `{invoice_data, validation}` payloads into formatted JSON.
4. **`components/` separates UI rendering into modular units**:
   - `header.py`: Renders branding and live Gemini API connection pill.
   - `sidebar.py`: Navigation radio, session metrics, and session reset.
   - `uploader.py`: File uploader, status progress bar, and extraction execution.
   - `invoice_preview.py`: High-detail image viewer with expander zoom.
   - `invoice_details.py`: Information cards for invoice number, date, supplier, currency, and totals.
   - `invoice_items.py`: Formatted table and interactive editor (`st.data_editor`) with live revalidation button.
   - `validation_panel.py`: Overall status banner, granular rule audit grid, and reconciliation summary.
   - `json_export.py`: Syntax-highlighted viewer and one-click download button.
5. **`tests/` test suite runs completely offline**: 85 automated tests verify all units, services, utilities, validation rules, and error boundaries in $< 1.0$ second without touching network or incurring API costs.

---

## 4. Deep Dive: How Each Component Works

### 4.1 `src/services.py`
- **Location on Disk**: `src/services.py`
- **Key Functions**:
  - `get_gemini_connection_status()`: Checks whether `GEMINI_API_KEY` is loaded and masks it for safe UI presentation (`AIza...4xY`).
  - `process_invoice_upload(image_bytes, filename)`: Safely writes bytes to a temporary file, runs image integrity verification, executes `extract_invoice()`, standardizes data via `clean_invoice_data()`, and runs `validate_invoice()`. Guarantees temporary file cleanup in a `finally` block.
  - `revalidate_edited_invoice(edited_data)`: Revalidates edited data locally using `clean_invoice_data()` and `validate_invoice()`, ensuring 0 latency and 0 API calls.
  - `create_session_history_record(filename, invoice_data, validation)`: Standardizes session audit records for real-time history tracking.

### 4.2 `src/utils.py`
- **Location on Disk**: `src/utils.py`
- **Key Functions**:
  - `safe_decimal(val)`: Converts values to Decimal, explicitly rejecting boolean masquerading (`True`/`False`), NaNs, and infinities.
  - `format_currency(amount, currency)`: Currency grouping formatting with two decimal places.
  - `format_quantity(qty)`: Formats quantities cleanly (`50`, `12.5`).
  - `calculate_item_line_total(quantity, unit_price)`: Multiplies using `ROUND_HALF_UP` Decimal rounding.
  - `build_items_dataframe(items, currency)`: Converts raw item dicts into a structured pandas DataFrame.
  - `generate_export_payload(invoice_data, validation)`: Produces pretty-printed JSON payloads.

### 4.3 `components/invoice_items.py` (Editing & Live Revalidation)
- **Location on Disk**: `components/invoice_items.py`
- **Functionality**:
  - Provides two tabs: **"📋 Line Items Table"** (read-only formatted view) and **"✏️ Edit Invoice & Live Revalidate"** (interactive editing).
  - In Edit mode, users can:
    - Edit metadata: Supplier Name, Invoice Number, Date, Currency.
    - Edit line items dynamically: Add rows, delete rows, update descriptions, quantities, and unit prices using `st.data_editor(num_rows="dynamic")`.
    - Edit totals: Subtotal, Tax Amount, Grand Total.
  - Clicking **"🔄 Validate Updated Invoice"** invokes `revalidate_edited_invoice()` without any AI calls, updates session state, updates the session history table, and triggers an immediate UI rerun to show the updated validation status and badges.

### 4.4 `components/validation_panel.py` (Rule Auditing)
- **Location on Disk**: `components/validation_panel.py`
- **Functionality**:
  - Displays overall status card (🟢 Valid, 🟡 Needs Review, 🔴 Failed).
  - Displays explicit error messages in red callout blocks and warnings in amber callout blocks.
  - Displays granular audit cards for:
    - Mandatory Fields Presence
    - Date Format (ISO 8601 `YYYY-MM-DD`)
    - Item Constraints (Quantity $> 0$, Price $\ge 0$)
    - Items Sum vs. Subtotal Match
    - Subtotal + Tax = Total Match
    - Grand Total Verification
  - Provides an expandable financial balance panel comparing reported subtotal, items sum, tax, and total.

---

## 5. End-to-End Processing Pipelines

### Pipeline A: Streamlit Interactive Web Application
```text
1. User opens web app: streamlit run app.py
2. User uploads image or clicks "📥 Load Sample Invoice"
   - components/invoice_preview.py renders high-resolution image preview.
3. User clicks "⚡ Extract Invoice with Gemini AI"
   - components/uploader.py displays multi-step st.status progress.
   - src/services.py (process_invoice_upload) verifies file size, extension, Pillow integrity.
   - src/extractor.py invokes Gemini 3 Flash Vision API with InvoiceData Pydantic schema.
   - src/extractor.py defensively cleans numbers, dates, and item objects.
   - src/validator.py calculates line totals, items sum, tax balance, and grand total.
   - Result is stored in st.session_state and recorded into session_history.
4. Web App routes to "📋 Extraction Results":
   - components/invoice_details.py displays overview cards.
   - components/validation_panel.py displays pass/fail status and granular check cards.
   - components/invoice_items.py renders formatted items table.
   - components/json_export.py renders JSON viewer and enables .json download.
5. User edits incorrect or missing data:
   - User switches to "✏️ Edit Invoice & Live Revalidate" tab.
   - User adjusts quantities, prices, or headers.
   - User clicks "🔄 Validate Updated Invoice".
   - src/services.py (revalidate_edited_invoice) runs 100% offline in < 5ms.
   - UI re-renders updated results immediately!
```

### Pipeline B: Command-Line Interface (CLI)
```text
1. Terminal Command: python main.py samples/invoice.png
2. main.py validates config and invokes extract_invoice().
3. extract_invoice() calls Gemini and cleans data.
4. validator.py verifies arithmetic and rules.
5. main.py saves output/result.json and prints execution summary box.
```

---

## 6. The Automated Test Suite (85 Tests)

The test suite covers the entire system with **85 automated tests** running in $< 1.0$s:

| Test File | Count | Scope |
| :--- | :---: | :--- |
| **`tests/test_cli.py`** | 5 | Argument parsing, missing image error, missing config error, result saving, traceback suppression. |
| **`tests/test_extractor.py`** | 26 | Strict numeric cleaning, boolean rejection, currency parsing, missing description preservation, invalid item preservation, image validation, config validation, markdown stripping, JSON decoding, 403 auth errors, 429 backoff retry, 404 model fallback, safety blocks. |
| **`tests/test_validator.py`** | 25 | Valid invoice matching, mismatched grand total, line discrepancies, missing mandatory fields, invalid calendar dates, missing item fields, empty item arrays, negative quantities, negative prices, negative totals, NaN/Inf/boolean rejection, optional subtotal/tax handling. |
| **`tests/test_services.py`** | 12 | Gemini connection status detection, key masking, upload byte validation, end-to-end processing pipeline, offline live revalidation on edited data, arithmetic discrepancy detection, session history record creation. |
| **`tests/test_utils.py`** | 17 | Decimal conversion, currency formatting, quantity formatting, item line total calculation with `ROUND_HALF_UP`, pandas DataFrame creation with corrupt object handling, and export JSON serialization. |
| **TOTAL** | **85** | **100% Passing Test Suite** |

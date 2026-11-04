# AI-Powered Invoice Data Extractor

A modular, clean, and reliable Python application that reads invoice images, extracts key details using the official Google Gemini SDK, validates financial arithmetic (line items, taxes, totals), and outputs clean, structured JSON.

Includes both an **Interactive Streamlit Web Application** (`streamlit run app.py`) and a **Command-Line Interface** (`python main.py samples/invoice.png`), sharing a single source of truth for AI extraction and arithmetic validation.

---

## 1. Project Description

Extracting data from invoices manually is tedious and error-prone. This application automates invoice processing using Google's **Gemini 3 Flash Preview** (`gemini-3-flash-preview`) model via the official `google-genai` Python SDK, featuring automatic fallback across the Google Flash family.

### Dual Interface: Web App + CLI
- **Interactive Web Application (`app.py`)**: Built with Streamlit, providing drag-and-drop file upload, full-resolution invoice preview, structured detail cards, interactive items editing with `st.data_editor`, live 100% offline revalidation, granular rule audit badges, syntax-highlighted JSON viewer, and one-click JSON file downloads.
- **Command-Line Interface (`main.py`)**: A fast, scriptable CLI tool for automated pipelines, server environments, and terminal workflows.

### Why Gemini 3 Flash?
- **Native Multimodal Understanding**: Reads images directly (tables, headers, small print, logos) without needing separate and brittle OCR preprocessing like Tesseract.
- **Structured JSON Support**: Supports strict schema enforcement (`response_schema=InvoiceData`), compelling the model to return valid JSON conforming to Pydantic definitions rather than free-form text.
- **Speed, Cost & Resilience**: Flash models offer high-speed, cost-effective inference with a generous free tier on Google AI Studio. Combined with automated multi-model fallback, extraction remains resilient even during peak API traffic spikes.

---

## 2. Key Features

- **Accurate Information Extraction**: Captures invoice number, issue date (standardized to `YYYY-MM-DD`), issuing supplier name (distinguishing the supplier from the "Bill To" customer), currency, line items, subtotal, tax amount, and total amount.
- **Built-in Financial & Arithmetic Validation**: Recalculates all line items ($\text{quantity} \times \text{unit price}$), verifies that their sum equals the subtotal, and checks that subtotal + tax equals the grand total (within a $0.05$ rounding tolerance).
- **Interactive Inline Editing & Offline Revalidation**: Users can correct OCR misreads or missing fields directly in the Streamlit web interface and click **"Validate Updated Invoice"** to rerun complete arithmetic validation instantly with **zero AI API calls**.
- **Graceful Error Handling**: Never exposes raw Python tracebacks to the user. Clear, human-readable error messages guide the user on missing files, bad formats, or unconfigured API keys.
- **Resilient Fallback & Exponential Backoff**: Handles temporary HTTP 429 (rate limits) and HTTP 503 (server busy) with exponential backoff retries, and automatically switches to alternative models (`gemini-3.5-flash`, `gemini-flash-latest`, `gemini-3.8-flash`) if a model is deprecated or unavailable.
- **Defensive Data Cleaning**: Sanitizes numbers (stripping commas, unit words like "pcs", and currency symbols), rejects non-finite numbers (NaN, Inf, booleans), and guarantees consistent JSON output where missing values are safely represented as `null`.
- **85 Comprehensive Offline Unit Tests**: Full test suite across 5 test files using `pytest` with mocked Gemini responses—running completely offline in $< 1.0$ seconds without consuming API credits.

---

## 3. Folder Structure

```text
invoice-extractor/
├── app.py                      # Interactive Streamlit Web Application entry point
├── main.py                     # CLI entry point (handles args, pipeline, and display)
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
│   ├── config.py               # Loads .env, resolves paths, and validates API key
│   ├── exceptions.py           # Custom domain exceptions (no raw tracebacks)
│   ├── extractor.py            # Gemini vision API integration, JSON prompt, cleaning & retries
│   ├── validator.py            # Financial logic checks (totals, items, dates, arithmetic)
│   ├── services.py             # Service layer coordinating UI with extractor & validator
│   └── utils.py                # Formatting helpers, Decimal math, and DataFrame builders
├── samples/
│   └── invoice.png             # Sample invoice image (Rivertech Supplies Ltd.)
├── output/
│   └── result.json             # Destination for CLI generated JSON output
├── tests/
│   ├── test_cli.py             # CLI argument, output generation, and error tests (5 tests)
│   ├── test_extractor.py       # Number sanitization, cleaning, image validation & API (26 tests)
│   ├── test_validator.py       # Financial arithmetic, required fields, and edge-cases (25 tests)
│   ├── test_services.py        # Connection status, upload handling, and offline revalidation (12 tests)
│   └── test_utils.py           # Currency formatting, quantities, decimal math, and JSON export (17 tests)
├── doc/
│   └── INVOICE_EXTRACTOR_DOCUMENTATION.md # Detailed technical architecture documentation
├── .env.example                # Template for environment configuration
├── .gitignore                  # Ignores .env, virtual environments, and caches
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Project dependencies (Streamlit, Pandas, Pillow, google-genai)
└── README.md                   # Human-written documentation and run instructions
```

---

## 4. Setup & Installation

### Requirements
- **Python**: Version 3.10+ recommended (compatible with Python 3.9+).
- **Operating System**: macOS, Linux, or Windows.

### Step 1: Clone or Navigate to the Folder
```bash
cd invoice-extractor
```

### Step 2: Create and Activate a Virtual Environment
```bash
# macOS / Linux:
python3 -m venv venv
source venv/bin/activate

# Windows (Command Prompt / PowerShell):
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 5. Setting Up Your Gemini API Key

You can obtain a free Google Gemini API key in under two minutes:

1. Visit [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click on **"Get API key"** and then **"Create API key"**.
4. Copy your key.

### Configure Environment Variables
Copy the example environment file to create your active `.env`:
```bash
cp .env.example .env
```

Open `.env` in any text editor and paste your key:
```ini
GEMINI_API_KEY=AIzaSyYourActualKeyGoesHere
GEMINI_MODEL=gemini-3-flash-preview
```

> **Security Note**: Never commit your `.env` file to version control. It is already listed in `.gitignore`.

---

## 6. How to Run

### Option A: Launch the Streamlit Web Application (Recommended)

To run the interactive web interface:
```bash
streamlit run app.py
```

The browser will automatically open at `http://localhost:8501`.

#### Web Interface Walkthrough:
1. **Dashboard**: View overall extraction statistics (Total Processed, Valid Invoices, Requiring Review, Errors) and recent session history. Click **"Load Sample Invoice"** to instantly test with the pre-bundled `samples/invoice.png`.
2. **Extract Invoice**: Drag and drop an invoice image (PNG, JPG, WEBP $\le 20\text{ MB}$) to preview the image. Click **"⚡ Extract Invoice with Gemini AI"** to run multimodal extraction.
3. **Extraction Results**:
   - **Header Cards**: View extracted Supplier, Invoice Number, Date, Currency, Subtotal, Tax, and Grand Total.
   - **Line Items Table**: Inspect formatted items with computed line totals.
   - **Live Editor & Revalidation**: Click the **"Edit Invoice & Live Revalidate"** tab to correct any values, add/remove rows, or update totals. Click **"Validate Updated Invoice"** to instantly revalidate offline with zero AI calls!
   - **Validation Panel**: Review overall status (🟢 Valid, 🟡 Needs Review, 🔴 Failed), individual check badges, error messages, and mathematical reconciliation details.
   - **JSON Export**: Inspect formatted JSON and click **"💾 Download JSON File"** to export.
4. **About**: In-depth architecture breakdown and engineering notes.

---

### Option B: Run via Command-Line Interface (CLI)

To run in headless or scriptable CLI mode:
```bash
python main.py samples/invoice.png
```

If you run without arguments, it displays usage guidance:
```bash
$ python main.py
usage: python main.py <path_to_invoice_image>

AI-Powered Invoice Data Extractor using Google Gemini.

positional arguments:
  image_path  Path to the invoice image file (PNG, JPG, JPEG, WEBP).

optional arguments:
  -h, --help  show this help message and exit
```

#### Sample Output in Console:
```json
{
  "invoice_data": {
    "invoice_number": "RT-2024-1052",
    "invoice_date": "2024-10-14",
    "supplier_name": "RIVERTECH SUPPLIES LTD.",
    "currency": "NPR",
    "items": [
      {
        "description": "HDPE Pipe 110mm (6m length)",
        "quantity": 50,
        "unit_price": 1250.0
      },
      {
        "description": "HDPE Elbow 90 degree 110mm",
        "quantity": 20,
        "unit_price": 450.0
      },
      {
        "description": "HDPE Coupling 110mm",
        "quantity": 30,
        "unit_price": 300.0
      },
      {
        "description": "Welding Service",
        "quantity": 10,
        "unit_price": 1500.0
      },
      {
        "description": "Delivery Charge",
        "quantity": 1,
        "unit_price": 5000.0
      }
    ],
    "subtotal": 100500.0,
    "tax_amount": 13065.0,
    "total_amount": 113565.0,
    "_metadata": {
      "model_used": "gemini-3-flash-preview",
      "model_fallback_applied": false,
      "attempt": 1,
      "image_size_bytes": 142105,
      "mime_type": "image/png"
    }
  },
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": [],
    "calculated_details": {
      "calculated_items_sum": 100500.0,
      "item_line_totals": [
        {
          "item_index": 1,
          "description": "HDPE Pipe 110mm (6m length)",
          "quantity": 50,
          "unit_price": 1250.0,
          "calculated_line_total": 62500.0
        },
        {
          "item_index": 2,
          "description": "HDPE Elbow 90 degree 110mm",
          "quantity": 20,
          "unit_price": 450.0,
          "calculated_line_total": 9000.0
        },
        {
          "item_index": 3,
          "description": "HDPE Coupling 110mm",
          "quantity": 30,
          "unit_price": 300.0,
          "calculated_line_total": 9000.0
        },
        {
          "item_index": 4,
          "description": "Welding Service",
          "quantity": 10,
          "unit_price": 1500.0,
          "calculated_line_total": 15000.0
        },
        {
          "item_index": 5,
          "description": "Delivery Charge",
          "quantity": 1,
          "unit_price": 5000.0,
          "calculated_line_total": 5000.0
        }
      ]
    }
  }
}
```

Followed by the execution summary card:
```text
=============================================
              EXECUTION SUMMARY
=============================================
  Invoice Status : VALID
  Errors Count   : 0
  Warnings Count : 0
  Saved JSON     : output/result.json
=============================================
```

---

## 7. How Validation Works

The validator in `src/validator.py` applies strict, independent business rules and financial checks:

### Critical Errors (Mark Invoice as INVALID: `is_valid: false`)
1. **Mandatory Top-Level Fields**: `invoice_number`, `invoice_date`, `supplier_name`, `items`, and `total_amount` must be present and non-empty.
2. **Calendar Date Validation**: `invoice_date` must be formatted as `YYYY-MM-DD` and represent a real calendar date (e.g., rejecting `2024-02-30`).
3. **Item Integrity**:
   - Must contain a non-empty list of items (empty array or non-list is rejected).
   - Description must not be missing or blank.
   - Quantity must be present, finite, and strictly positive ($\text{quantity} > 0$).
   - Unit price must be present, finite, and non-negative ($\text{unit\_price} \ge 0$).
4. **Monetary Sanity Checks**: Rejects negative amounts for `subtotal`, `tax_amount`, and `total_amount`. Rejects non-finite numbers (`NaN`, `Infinity`) and booleans (`True`/`False`).
5. **Item Line Calculation**: Computes per-item line totals ($\text{quantity} \times \text{unit price}$) and exposes them under `calculated_details.item_line_totals` for auditability.
6. **Items Sum vs. Subtotal**: Verifies that the computed line totals sum matches the extracted subtotal within a $0.05$ rounding tolerance:
   $$\lvert \sum \text{line\_totals} - \text{subtotal} \rvert \le 0.05$$
7. **Subtotal + Tax vs. Grand Total**: Verifies that subtotal + tax equals the grand total within $0.05$:
   $$\lvert (\text{subtotal} + \text{tax\_amount}) - \text{total\_amount} \rvert \le 0.05$$
8. **Direct Grand Total Consistency**: Confirms that items total (+ tax) matches the grand total.

### Informational Warnings (Non-Critical Notifications)
- **Missing Optional Subtotal**: If an invoice omits a subtotal, the validator warns that subtotal verification was skipped rather than failing an otherwise valid invoice.
- **Missing Optional Tax**: If tax is omitted, the validator verifies if the items match the grand total directly (tax-exempt invoice) or warns that the tax amount could not be independently checked.

---

## 8. Error Handling & Retry Architecture

The application ensures that **a user never sees an unhandled Python traceback**.

| Failure Mode | Module | Mechanism | User-Facing Notice |
| :--- | :--- | :--- | :--- |
| **Missing Image File** | `extractor.py` | Validated by `_validate_image_file` pre-flight. | `[Error: Invalid Image] Invoice image file not found at: ...` |
| **Unsupported Format** | `extractor.py` | Restricts extensions to `.png`, `.jpg`, `.jpeg`, `.webp`. | `[Error: Invalid Image] Unsupported file format '.pdf'. Supported: .png, .jpg, .jpeg, .webp` |
| **Corrupted Image** | `extractor.py` | Verifies image integrity using `Pillow.Image.verify()`. | `[Error: Invalid Image] Image file is corrupted or not a valid image` |
| **Oversized Image** | `extractor.py` | Enforces a maximum limit of 20 MB before loading into memory. | `[Error: Invalid Image] Image file exceeds maximum allowed size of 20 MB` |
| **Missing API Key** | `config.py` | Fail-fast check before network invocation. | `[Error: Configuration] GEMINI_API_KEY is missing or invalid. Please copy '.env.example' to '.env'...` |
| **Fatal Auth Error (403)** | `extractor.py` | Detects unauthorized key; aborts immediately without cycling models. | `[Error: Gemini API] Authentication failed: The configured GEMINI_API_KEY is invalid or unauthorized.` |
| **Rate Limit (429) / Busy (503)** | `extractor.py` | Retries with exponential backoff ($1.5^n$ seconds up to 6.0s). | `[Notice] Model 'gemini-3-flash-preview' returned temporary load notice. Retrying in 1.5s...` |
| **Model Unavailable (404)** | `extractor.py` | Automatically switches to next fallback model in `GEMINI_FALLBACK_MODELS`. | `[Notice] Model 'gemini-2.5-flash' unavailable. Automatically switching to fallback model 'gemini-3-flash-preview'...` |
| **Safety Filter Block** | `extractor.py` | Inspects `candidates[0].finish_reason` for `SAFETY` or `MAX_TOKENS`. | `[Error: Gemini API] Invoice processing was blocked by safety filters (finish_reason: SAFETY).` |
| **Malformed AI JSON** | `extractor.py` | Strips markdown fences, retries parsing, reports snippet on failure. | `[Error: Data Parsing] Failed to decode model response as JSON: ...` |

---

## 9. Running Automated Tests

The project includes **85 automated unit and integration tests** across 5 test suites, running completely offline with zero API cost:

```bash
pytest -v
```

### Test Suite Overview:
- [**`tests/test_validator.py`**](file:///tests/test_validator.py) (25 tests):
  - Happy path matching all totals
  - Mismatched grand total and mismatched line item amounts
  - Missing mandatory fields (supplier, invoice date, invoice number)
  - Invalid calendar dates (e.g. non-existent leap days or malformed strings)
  - Missing item descriptions, missing quantities, and missing unit prices (must fail)
  - Empty items array and non-list items data types
  - Negative values (quantity, unit price, subtotal, tax, total)
  - Rejection of `NaN`, `Infinity`, and Booleans
  - Missing optional subtotal and tax warnings
- [**`tests/test_extractor.py`**](file:///tests/test_extractor.py) (26 tests):
  - Strict numeric cleaning and currency/unit parsing
  - Rejection of ambiguous numeric strings (`abc123def`)
  - Preservation of missing descriptions as `None` (no placeholder text)
  - Preservation of invalid item objects
  - File existence, directory checks, size limits, and corrupted image detection
  - API key configuration validation
  - Markdown fence stripping and JSON parsing
  - Fatal 403 authentication handling (no fallback cycling)
  - 429 rate limit exponential backoff retry
  - 404 model fallback switching
  - Safety filter blocked candidates detection
  - Complete mocked extraction pipeline with metadata
- [**`tests/test_cli.py`**](file:///tests/test_cli.py) (5 tests):
  - No arguments displays usage and exits with code 1
  - Nonexistent image path exits with code 1 and clean error (no traceback)
  - Missing configuration exits with code 1 and clean error
  - Successful extraction writes `output/result.json` and prints summary card
  - Suppresses raw Python tracebacks on API errors
- [**`tests/test_services.py`**](file:///tests/test_services.py) (12 tests):
  - Live Gemini API connection detection and key masking
  - Upload validation (empty file, oversized $\ge 20\text{ MB}$, invalid extension, corrupted image)
  - End-to-end service orchestration pipeline
  - Offline revalidation with valid modifications
  - Offline revalidation detecting line item arithmetic discrepancies
  - Session history audit record generation
- [**`tests/test_utils.py`**](file:///tests/test_utils.py) (17 tests):
  - Safe decimal conversion rejecting booleans, infinities, and NaNs
  - Currency formatting with standard grouping (`NPR 113,565.00`) and negative handling
  - Quantity clean formatting (integers vs decimals)
  - Decimal line total calculation with `ROUND_HALF_UP`
  - DataFrame generation with styled columns and corrupt row handling
  - JSON export payload serialization

---

## 10. Clean Packaging & Submission

When packaging this project for submission, virtual environments, caches, OS metadata, and secrets must be excluded.

Use this clean packaging command:
```bash
zip -r invoice_extractor_submission.zip invoice-extractor \
  -x "*/venv/*" \
  -x "*/.pytest_cache/*" \
  -x "*/__pycache__/*" \
  -x "*/.DS_Store" \
  -x "*/.env" \
  -x "*/__MACOSX/*"
```

The resulting zip contains all source code, tests, sample invoice, requirements, and documentation ready for clean evaluation.

---

## 11. Complete Step-by-Step Setup & Run Guide (Terminal CLI & Web UI)

This section provides comprehensive, beginner-friendly instructions for setting up the environment, running the terminal CLI with sample/custom invoice images, launching the Streamlit Web UI, and troubleshooting.

### 11.1 Full Environment Setup from Scratch

#### Step 1: Open Terminal & Navigate to Project Directory
```bash
cd ~/Desktop/invoice-extractor
```

#### Step 2: Create a Virtual Environment (`venv`)
```bash
# macOS / Linux:
python3 -m venv venv

# Windows:
python -m venv venv
```

#### Step 3: Activate the Virtual Environment
> **Note for macOS users**: Modern macOS does not have a global `python` command. Activating `venv` provides the `python` command alias!

```bash
# macOS / Linux:
source venv/bin/activate

# Windows (Command Prompt):
venv\Scripts\activate.bat

# Windows (PowerShell):
venv\Scripts\Activate.ps1
```
When active, your terminal prompt will display `(venv)` on the left.

#### Step 4: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 5: Configure Your Gemini API Key in `.env`
1. Visit [Google AI Studio](https://aistudio.google.com/) and click **"Create API Key"**.
2. Copy `.env.example` to create your active `.env`:
   ```bash
   cp .env.example .env
   ```
3. Open `.env` and paste your key:
   ```ini
   GEMINI_API_KEY=AIzaSyYourActualKeyHere
   GEMINI_MODEL=gemini-3-flash-preview
   GEMINI_FALLBACK_MODELS=gemini-3-flash-preview,gemini-3.5-flash,gemini-flash-latest,gemini-3.8-flash
   ```

---

### 11.2 Running from the Terminal (CLI)

#### A. Running with the Bundled Sample Invoice
To process the bundled invoice image (`samples/invoice.png` from Rivertech Supplies Ltd.):
```bash
# Ensure virtual environment is active
source venv/bin/activate

# Run extraction
python main.py samples/invoice.png
```

#### B. Running with Any Custom Invoice
You can pass any relative or absolute path to your own invoice image:
```bash
python main.py /path/to/my_invoice.jpg
# or
python main.py samples/another_receipt.png
```
* **Supported image formats**: `.png`, `.jpg`, `.jpeg`, `.webp` (up to 20 MB).
* **CLI Result**:
  1. Full validated JSON payload is printed to the terminal.
  2. Execution Summary card is displayed.
  3. Structured JSON file is automatically written to `output/result.json`.

---

### 11.3 Running the Interactive Web Application (Streamlit UI) & Manual Upload Guide

#### Exact Terminal Command Sequence:
Copy and paste this command block directly into your terminal:

```bash
cd /Users/bhaskarbudha/Desktop/invoice-extractor
source venv/bin/activate
streamlit run app.py
```

Streamlit will launch a local web server and print:
```text
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```
Open `http://localhost:8501` in Chrome, Safari, or your preferred browser.

---

#### Step-by-Step User Guide: Manually Uploading & Processing Invoices from the Web UI

```text
[Step 1] Upload Image        [Step 2] Preview & Zoom      [Step 3] AI Extraction
     Drag & Drop       --->   Verify Resolution     --->   Click "Extract Invoice"
  (.png, .jpg, .webp)         Check Dimensions             Watch Multi-Step Progress
                                                                   |
                                                                   v
[Step 6] Export JSON         [Step 5] Offline Revalidate   [Step 4] Results & Edit
  Click "Download JSON" <---  0 AI Calls / 0 Quota  <---  High-Contrast Cards
  Get Structured File         Instant Math Recalculation   Interactive Items Table
```

1. **Step 1: Navigate to "Extract Invoice"**
   * On the left sidebar navigation, click on **"Extract Invoice"** (or click **"Upload Invoice"** directly from the Dashboard).

2. **Step 2: Manually Upload Your Invoice Image**
   * Locate the drag-and-drop upload zone labeled **"Upload Invoice Image"**.
   * Click **"Browse files"** to select an image from your computer, or simply drag and drop the file directly into the box.
   * **Supported file types**: PNG, JPG, JPEG, WEBP (up to 20 MB).
   * *Tip*: You can upload the pre-bundled sample invoice by selecting `samples/invoice.png`, or upload any real receipt/bill.

3. **Step 3: Inspect the Instant Live Image Preview**
   * As soon as you select a file, the application immediately displays an image preview along with file metadata (file name, image format, dimensions in pixels, and file size).
   * Click the **"Expand high-resolution invoice preview"** expander if you want to inspect fine print, tiny line items, or tax disclaimers at full resolution.

4. **Step 4: Run Multimodal AI Extraction**
   * Click the primary action button: **"Extract Invoice with Gemini AI"**.
   * A multi-step progress indicator guides you through the process:
     1. Validating image format and size limits
     2. Connecting to Google Gemini multimodal vision model
     3. Extracting structured financial schema with Pydantic
     4. Recalculating independent arithmetic and business validation rules

5. **Step 5: Review Extracted Details & Line Items**
   * Once extraction finishes, you are automatically shown the **"Extraction Results"**:
     * **Executive Metadata Cards**: Supplier Name, Invoice Number, Invoice Date, Currency, Subtotal, Tax Amount, and Grand Total.
     * **Line Items Table**: Description, Quantity, Unit Price, and calculated Line Total ($\text{Quantity} \times \text{Unit Price}$).

6. **Step 6: Interactive Inline Editing & Live Offline Revalidation**
   * If any item was misread or you want to update quantities or prices:
     * Switch to the **"Edit Invoice & Live Revalidate"** tab.
     * Click directly into any cell of the table to modify descriptions, change quantities, or add/remove rows.
     * Click the **"Re-validate Invoice Data"** button.
     * **Important**: Revalidation is **100% offline**—it runs on your local computer using Python Decimal arithmetic with **zero API calls, zero latency, and zero quota consumption**.

7. **Step 7: Check the Validation Audit Panel**
   * Look at the **Validation Status Banner**:
     * **VALID**: All financial checks passed and arithmetic matches.
     * **NEEDS REVIEW**: Optional fields omitted (e.g., tax-exempt invoice).
     * **FAILED**: Mathematical mismatch ($\Delta > 0.05$) or missing required field.
   * Expand the **Mathematical Reconciliation** box to inspect the exact equation: $\text{Items Sum} + \text{Tax} = \text{Grand Total}$.

8. **Step 8: View & Download the Structured JSON**
   * Inspect the formatted, syntax-highlighted JSON under the **JSON Output** viewer.
   * Click **"Download JSON File"** to save the structured file (`<invoice_number>_extracted.json`) directly to your machine.

---

### 11.4 Running the Test Suite
To verify the entire system offline (85 passing tests):
```bash
source venv/bin/activate
pytest -v
```

---

### 11.5 Common Troubleshooting

* **Issue: `zsh: command not found: python`**
  - **Solution**: Activate your virtual environment first: `source venv/bin/activate`. Alternatively, run `./venv/bin/python main.py samples/invoice.png`.
* **Issue: `[Notice] Model returned temporary load notice (Rate Limit)`**
  - **What it means**: Your API key is **100% valid and working**! Google only checks rate limits for authenticated keys. The free tier limits requests to 15 per minute, or the preview model is experiencing temporary global traffic. Our automatic fallback system handles this by waiting 1.5s or switching to `gemini-3.5-flash`.
* **Issue: `[Error: Configuration] GEMINI_API_KEY is missing or invalid`**
  - **Solution**: Check that `.env` exists in the project root directory and contains your real API key (not `your_key_here`).
* **Issue: Streamlit Port 8501 is already in use**
  - **Solution**: Run on another port: `streamlit run app.py --server.port 8502`.

---

### 11.6 Running Directly with Docker (Containerized Setup)

Docker allows you to run the entire application inside an isolated, production-grade container without needing to configure a local Python virtual environment.

#### Prerequisites
* Make sure **Docker** or **Docker Desktop** is installed and running on your machine.

#### Step 1: Build the Docker Image
From the project root directory, run:
```bash
cd /Users/bhaskarbudha/Desktop/invoice-extractor
docker build -t invoice-extractor .
```
*(This builds a lightweight Python 3.11 image, installs all dependencies, and sets up health checks).*

#### Step 2: Run the Docker Container
Choose one of the following methods to start the container:

**Method A: Using Your `.env` File (Recommended for Security)**:
```bash
docker run -d -p 8501:8501 --env-file .env --name invoice-app invoice-extractor
```
*(This safely passes your `GEMINI_API_KEY` without exposing it in terminal history).*

**Method B: Passing the API Key Directly**:
```bash
docker run -d -p 8501:8501 -e GEMINI_API_KEY="AIzaSyYourActualKeyHere" --name invoice-app invoice-extractor
```

#### Step 3: Open the Web UI
Open your browser and navigate to:
```text
http://localhost:8501
```

#### Step 4: Essential Docker Management Commands
```bash
# View live application and extraction logs
docker logs -f invoice-app

# Check container status
docker ps

# Stop the container
docker stop invoice-app

# Start the container again
docker start invoice-app

# Remove the container
docker rm -f invoice-app
```

---

### 11.7 Cloud Deployment & Sharing Links with Others

> [!NOTE]
> `http://localhost:8501` only works on **your own computer**. To share a live link with assessors, clients, or team members, use one of the deployment methods below:

#### Option A: Streamlit Community Cloud (Recommended — 100% Free Public URL)
1. Push your code to GitHub (`git push origin main`).
2. Log in at [share.streamlit.io](https://share.streamlit.io) with GitHub.
3. Select repo `invoice-extractor`, branch `main`, and main file `app.py`.
4. In **Advanced Settings $\rightarrow$ Secrets**, paste:
   ```toml
   GEMINI_API_KEY = "AIzaSy..."
   ```
5. Click **Deploy**. You will receive a permanent public HTTPS link (e.g., `https://your-app.streamlit.app`).

#### Option B: Deploy Container to Google Cloud Run
```bash
gcloud run deploy invoice-extractor \
  --source . \
  --port 8501 \
  --set-env-vars GEMINI_API_KEY="AIzaSy..." \
  --allow-unauthenticated
```

#### Option C: Instant Temporary Public Link via Cloudflare (30 Seconds)
To share your currently running local Docker container with someone right now without deploying to the cloud:
```bash
brew install cloudflared
cloudflared tunnel --url http://localhost:8501
```
Cloudflare will provide a temporary secure public link (e.g. `https://xxxx.trycloudflare.com`) pointing directly to your local instance.


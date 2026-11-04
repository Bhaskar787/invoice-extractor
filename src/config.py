"""
Configuration Module.

Loads environment variables from .env and exposes application-wide settings.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

from src.exceptions import ConfigurationError

# Resolve the project root directory (one level up from src/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Explicit path to the .env file in the project root
ENV_FILE = BASE_DIR / ".env"

# Load variables from .env into the process environment
load_dotenv(dotenv_path=ENV_FILE)

# Read the Gemini API key and model from the environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEFAULT_MODEL = "gemini-3-flash-preview"
GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or DEFAULT_MODEL).strip()


def validate_config(api_key: str | None = None) -> str:
    """
    Validates that a valid Gemini API key is configured.

    Args:
        api_key: Optional API key string to validate. If omitted, uses GEMINI_API_KEY.

    Returns:
        str: The validated non-empty API key.

    Raises:
        ConfigurationError: If the API key is missing or set to the placeholder.
    """
    candidate = api_key if api_key is not None else GEMINI_API_KEY
    key = (candidate or "").strip()
    if not key or key in ("", "your_key_here"):
        raise ConfigurationError(
            "GEMINI_API_KEY is missing or invalid.\n"
            "Please copy '.env.example' to '.env' and add your Gemini API key:\n"
            "    cp .env.example .env\n"
            "Then open '.env' and set: GEMINI_API_KEY=your_actual_api_key"
        )
    return key

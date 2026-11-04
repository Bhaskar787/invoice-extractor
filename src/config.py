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

# Read the Gemini API key and model from the environment or Streamlit Cloud secrets
def _resolve_gemini_api_key() -> str | None:
    key = os.getenv("GEMINI_API_KEY")
    if key and key.strip() and key.strip() != "your_key_here":
        return key.strip()
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            sec_val = st.secrets["GEMINI_API_KEY"]
            if sec_val and str(sec_val).strip():
                return str(sec_val).strip()
    except Exception:
        pass
    return key


def _resolve_gemini_model() -> str:
    model = os.getenv("GEMINI_MODEL")
    if model and model.strip():
        return model.strip()
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_MODEL" in st.secrets:
            sec_model = st.secrets["GEMINI_MODEL"]
            if sec_model and str(sec_model).strip():
                return str(sec_model).strip()
    except Exception:
        pass
    return "gemini-3-flash-preview"


GEMINI_API_KEY = _resolve_gemini_api_key()
DEFAULT_MODEL = "gemini-3-flash-preview"
GEMINI_MODEL = _resolve_gemini_model()


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
    candidate = api_key if api_key is not None else _resolve_gemini_api_key()
    key = (candidate or "").strip()
    if not key or key in ("", "your_key_here"):
        raise ConfigurationError(
            "GEMINI_API_KEY is missing or invalid.\n"
            "Please copy '.env.example' to '.env' and add your Gemini API key:\n"
            "    cp .env.example .env\n"
            "Then open '.env' and set: GEMINI_API_KEY=your_actual_api_key"
        )
    return key


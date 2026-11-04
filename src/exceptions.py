"""
Custom Exception Classes.

Defines custom, human-friendly exceptions for the Invoice Extractor
application to prevent raw stack traces and enable graceful handling.
"""

from __future__ import annotations


class InvoiceExtractorError(Exception):
    """Base exception for all invoice extractor application errors."""
    pass


class ConfigurationError(InvoiceExtractorError):
    """Raised when environment variables or configurations are missing/invalid."""
    pass


class ImageValidationError(InvoiceExtractorError):
    """Raised when an invoice image path is invalid or format is unsupported."""
    pass


class APIExtractionError(InvoiceExtractorError):
    """Raised when communication with the Google Gemini API fails."""
    pass


class JSONParsingError(InvoiceExtractorError):
    """Raised when the AI model reply cannot be decoded into valid JSON."""
    pass

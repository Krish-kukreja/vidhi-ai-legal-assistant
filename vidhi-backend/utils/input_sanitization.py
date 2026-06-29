"""
Input sanitization utilities to prevent prompt injection and improve LLM response quality.

Security measures:
- Strip/escape special characters that could be used for prompt injection
- Limit input length to prevent token exhaustion
- Filter inappropriate content
- Normalize whitespace and formatting
"""

import re
from typing import Optional


# Maximum input lengths
MAX_CHAT_INPUT_LENGTH = 5000  # characters
MAX_DOCUMENT_TEXT_LENGTH = 50000  # characters for document content
MAX_FILENAME_LENGTH = 255


def sanitize_chat_input(text: str, max_length: int = MAX_CHAT_INPUT_LENGTH) -> str:
    """
    Sanitize user chat input before sending to LLM.

    Args:
        text: Raw user input
        max_length: Maximum allowed length

    Returns:
        Sanitized text safe for LLM processing
    """
    if not text or not isinstance(text, str):
        return ""

    # Truncate to max length
    text = text[:max_length]

    # Normalize whitespace (collapse multiple spaces/newlines)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    # Remove null bytes and other control characters (except newlines/tabs)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    # Escape potential prompt injection patterns
    # Remove attempts to override system instructions
    injection_patterns = [
        r"ignore\s+(previous|all|above)\s+instructions?",
        r"disregard\s+(previous|all|above)",
        r"forget\s+(previous|all|above)",
        r"you\s+are\s+now",
        r"new\s+instructions?:",
        r"system\s*:",
        r"assistant\s*:",
        r"<\|.*?\|>",  # Special tokens
        r"\[INST\]",  # Instruction markers
        r"\[/INST\]",
    ]

    for pattern in injection_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Remove excessive repetition (potential DoS)
    # Replace 4+ repeated characters with 3
    text = re.sub(r"(.)\1{3,}", r"\1\1\1", text)

    return text.strip()


def sanitize_document_text(
    text: str, max_length: int = MAX_DOCUMENT_TEXT_LENGTH
) -> str:
    """
    Sanitize document text before processing.
    Less aggressive than chat input since documents may have special formatting.

    Args:
        text: Raw document text
        max_length: Maximum allowed length

    Returns:
        Sanitized document text
    """
    if not text or not isinstance(text, str):
        return ""

    # Truncate to max length
    text = text[:max_length]

    # Remove null bytes and control characters
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    # Normalize excessive whitespace but preserve paragraph breaks
    text = re.sub(r" +", " ", text)  # Multiple spaces to single
    text = re.sub(r"\n{4,}", "\n\n\n", text)  # Max 3 newlines

    return text.strip()


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other attacks.

    Args:
        filename: Raw filename from user

    Returns:
        Safe filename
    """
    if not filename or not isinstance(filename, str):
        return "unnamed_file"

    # Remove path components (prevent directory traversal)
    filename = filename.replace("\\", "/").split("/")[-1]

    # Remove or replace dangerous characters
    # Allow: alphanumeric, dash, underscore, dot
    filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)

    # Prevent hidden files
    if filename.startswith("."):
        filename = "file_" + filename

    # Prevent multiple extensions (e.g., file.pdf.exe)
    parts = filename.split(".")
    if len(parts) > 2:
        filename = "_".join(parts[:-1]) + "." + parts[-1]

    # Truncate to max length
    if len(filename) > MAX_FILENAME_LENGTH:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        max_name_len = MAX_FILENAME_LENGTH - len(ext) - 1
        filename = name[:max_name_len] + ("." + ext if ext else "")

    return filename or "unnamed_file"


def validate_language_code(lang_code: str) -> Optional[str]:
    """
    Validate language code against supported languages.

    Args:
        lang_code: Language code from user (e.g., 'en', 'hi', 'ta')

    Returns:
        Validated language code or None if invalid
    """
    # List of supported Indian language codes
    SUPPORTED_LANGUAGES = {
        "en",
        "hi",
        "bn",
        "te",
        "mr",
        "ta",
        "gu",
        "kn",
        "ml",
        "pa",
        "or",
        "as",
        "ur",
        "sa",
        "ks",
        "sd",
        "ne",
        "ko",
        "mai",
        "mni",
        "doi",
        "sat",
    }

    if not lang_code or not isinstance(lang_code, str):
        return None

    lang_code = lang_code.lower().strip()

    # Validate format (2-3 letter code)
    if not re.match(r"^[a-z]{2,3}$", lang_code):
        return None

    return lang_code if lang_code in SUPPORTED_LANGUAGES else None


def sanitize_session_id(session_id: str) -> str:
    """
    Sanitize session ID to prevent injection attacks.

    Args:
        session_id: Raw session ID from user

    Returns:
        Safe session ID (alphanumeric + dash/underscore only)
    """
    if not session_id or not isinstance(session_id, str):
        return "default_session"

    # Allow only alphanumeric, dash, underscore
    session_id = re.sub(r"[^a-zA-Z0-9_-]", "", session_id)

    # Limit length
    session_id = session_id[:100]

    return session_id or "default_session"


def check_content_safety(text: str) -> tuple[bool, Optional[str]]:
    """
    Basic content safety check for inappropriate content.

    Args:
        text: Text to check

    Returns:
        Tuple of (is_safe, reason_if_unsafe)
    """
    if not text:
        return True, None

    text_lower = text.lower()

    # Check for extremely long inputs (potential DoS)
    if len(text) > MAX_CHAT_INPUT_LENGTH * 2:
        return False, "Input too long"

    # Check for excessive repetition (potential DoS)
    if re.search(r"(.{10,})\1{10,}", text):
        return False, "Excessive repetition detected"

    # Check for binary/encoded content that shouldn't be in text
    if re.search(r"[\x00-\x08\x0B\x0C\x0E-\x1F]{10,}", text):
        return False, "Invalid characters detected"

    return True, None


# Convenience function for API endpoints
def sanitize_api_input(
    text: Optional[str] = None,
    filename: Optional[str] = None,
    session_id: Optional[str] = None,
    language: Optional[str] = None,
    is_document: bool = False,
) -> dict:
    """
    Sanitize all inputs for an API request.

    Args:
        text: User text input
        filename: Uploaded filename
        session_id: Session identifier
        language: Language code
        is_document: Whether text is from a document (less aggressive sanitization)

    Returns:
        Dictionary with sanitized values
    """
    result = {}

    if text is not None:
        if is_document:
            result["text"] = sanitize_document_text(text)
        else:
            result["text"] = sanitize_chat_input(text)

        # Check content safety
        is_safe, reason = check_content_safety(result["text"])
        result["is_safe"] = is_safe
        result["safety_reason"] = reason

    if filename is not None:
        result["filename"] = sanitize_filename(filename)

    if session_id is not None:
        result["session_id"] = sanitize_session_id(session_id)

    if language is not None:
        result["language"] = validate_language_code(language)

    return result

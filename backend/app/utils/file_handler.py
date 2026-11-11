import hashlib
import os
import re
import uuid
from pathlib import Path
from typing import Tuple

# Maximum upload size: 10 MB
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Allowed extensions and MIME types
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpeg",
    "image/jpg": ".jpg",
}

# Magic signatures
FILE_SIGNATURES = {
    b"%PDF": "application/pdf",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
}

# Base upload directory
BASE_UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "invoices"
BASE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class FileValidationError(Exception):
    """Raised when an uploaded file fails validation."""
    pass


def sanitize_filename(filename: str) -> str:
    """Sanitizes user provided filename to prevent directory traversal or unsafe chars."""
    if not filename:
        return "unnamed_document"
    # Remove any directory separators
    filename = os.path.basename(filename)
    # Remove any null bytes or path traversal
    filename = filename.replace("\x00", "").replace("..", "")
    # Allow alphanumeric, dashes, underscores, dots
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    return filename or "unnamed_document"


def compute_sha256(content: bytes) -> str:
    """Computes SHA-256 hash of raw file bytes."""
    return hashlib.sha256(content).hexdigest()


def validate_file_content(content: bytes, original_filename: str, declared_mime: str = "") -> Tuple[str, str]:
    """Validates file size, non-emptiness, extension, declared mime, and actual magic bytes.

    Returns:
        (detected_mime, safe_extension)

    Raises:
        FileValidationError if file is invalid.
    """
    file_size = len(content)

    if file_size == 0:
        raise FileValidationError("Uploaded file is empty (0 bytes).")

    if file_size > MAX_FILE_SIZE_BYTES:
        raise FileValidationError(
            f"File size exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB ({file_size} bytes)."
        )

    # Check extension
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"Unsupported file extension '{ext}'. Supported formats: PDF, PNG, JPG, JPEG."
        )

    # Check magic byte signatures
    detected_mime = None
    if content.startswith(b"%PDF"):
        detected_mime = "application/pdf"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_mime = "image/png"
    elif content.startswith(b"\xff\xd8\xff"):
        detected_mime = "image/jpeg"
    else:
        raise FileValidationError(
            "File header signature does not match any supported format (PDF, PNG, JPEG). The file may be corrupt or mislabeled."
        )

    # Check that extension matches detected MIME
    if detected_mime == "application/pdf" and ext != ".pdf":
        raise FileValidationError(f"Mismatched file format: content is PDF but extension is '{ext}'.")
    if detected_mime == "image/png" and ext != ".png":
        raise FileValidationError(f"Mismatched file format: content is PNG but extension is '{ext}'.")
    if detected_mime == "image/jpeg" and ext not in [".jpg", ".jpeg"]:
        raise FileValidationError(f"Mismatched file format: content is JPEG but extension is '{ext}'.")

    return detected_mime, ext


def save_uploaded_file(content: bytes, original_filename: str) -> Tuple[str, str, int, str]:
    """Saves file to secure backend upload directory with unique server-side filename.

    Returns:
        (relative_storage_path, unique_server_filename, file_size, sha256_hash)
    """
    sha256 = compute_sha256(content)
    detected_mime, ext = validate_file_content(content, original_filename)

    unique_server_filename = f"{uuid.uuid4().hex}{ext}"
    target_path = BASE_UPLOAD_DIR / unique_server_filename

    # Ensure no path traversal
    if not str(target_path.resolve()).startswith(str(BASE_UPLOAD_DIR.resolve())):
        raise FileValidationError("Unsafe target path detected.")

    with open(target_path, "wb") as f:
        f.write(content)

    relative_path = f"uploads/invoices/{unique_server_filename}"
    return relative_path, unique_server_filename, len(content), sha256


def get_absolute_file_path(relative_path: str) -> Path:
    """Safely resolves document path within uploads directory."""
    if not relative_path:
        raise FileNotFoundError("Empty document path provided.")

    backend_dir = Path(__file__).resolve().parent.parent.parent
    clean_path = Path(relative_path.lstrip("/"))
    abs_path = (backend_dir / clean_path).resolve()

    # Safety check: must reside inside backend directory
    if not str(abs_path).startswith(str(backend_dir.resolve())):
        raise PermissionError("Access to path outside backend is denied.")

    if not abs_path.exists() or not abs_path.is_file():
        raise FileNotFoundError(f"Document file not found at {abs_path}")

    return abs_path

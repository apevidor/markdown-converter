"""Security module — MIME validation, path safety, filename sanitization."""

import logging
import re
from io import BytesIO
from pathlib import Path

logger = logging.getLogger("securedoc2md.security")

try:
    import magic
except ImportError:
    magic = None  # type: ignore[assignment]

ALLOWED_MIME_TYPES: dict[str, list[str]] = {
    "pdf": ["application/pdf"],
    "docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    ],
    "xlsx": [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
    ],
}

MAX_FILE_BYTES: int = 50 * 1024 * 1024
TEMP_DIR_BASE: Path = Path("/tmp/secure_doc2md")


def _flat_allowed_mimes() -> set[str]:
    return {mime for mimes in ALLOWED_MIME_TYPES.values() for mime in mimes}


def detect_mime_type(data: bytes) -> str:
    if magic is None:
        raise RuntimeError("python-magic library is not installed")
    sample = data[:2048]
    mime_type = magic.from_buffer(sample, mime=True)
    if isinstance(mime_type, bytes):
        mime_type = mime_type.decode("utf-8", errors="replace")
    result = str(mime_type).lower()
    logger.info("MIME detected: len=%d sample_hex=%s… => %s", len(data), sample[:16].hex(), result)
    return result


def validate_mime(data: bytes) -> bool:
    try:
        detected = detect_mime_type(data)
    except RuntimeError:
        raise
    allowed = _flat_allowed_mimes()
    ok = detected in allowed
    logger.info("MIME validation: detected=%s allowed=%s => %s", detected, allowed, ok)
    return ok


def check_file_size(data: BytesIO, max_bytes: int = MAX_FILE_BYTES) -> bool:
    data.seek(0, 2)
    size = data.tell()
    data.seek(0)
    ok = size <= max_bytes
    logger.info("Size check: %d bytes (limit=%d) => %s", size, max_bytes, ok)
    return ok


def sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    safe = safe.strip("._-")
    if not safe:
        safe = "untitled"
    if "." in safe:
        safe = safe.rsplit(".", 1)[0]
    safe = safe[:197]
    result = f"{safe}.md"
    logger.info("Filename sanitized: %r => %r", name, result)
    return result


def safe_path(file_path: Path, base_dir: Path) -> bool:
    try:
        resolved_file = file_path.resolve()
        resolved_base = base_dir.resolve()
    except (OSError, RuntimeError):
        return False
    ok = str(resolved_file).startswith(str(resolved_base) + "/") \
        or resolved_file == resolved_base
    logger.info("Path check: file=%s base=%s => %s", resolved_file, resolved_base, ok)
    return ok
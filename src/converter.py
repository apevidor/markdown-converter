"""Converter module — isolated MarkItDown wrapper for safe file-to-Markdown conversion."""

import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import os
import shutil
import uuid

from markitdown import MarkItDown
from markitdown._exceptions import FileConversionException

from src.security import TEMP_DIR_BASE, safe_path, sanitize_filename

logger = logging.getLogger("securedoc2md.converter")


@dataclass
class ConversionResult:
    content: str
    filename: str
    error: str | None


def convert_to_markdown(file_bytes: BytesIO, original_name: str) -> ConversionResult:
    output_name = sanitize_filename(original_name)
    original_suffix = Path(original_name).suffix
    temp_name = f"{uuid.uuid4().hex}{original_suffix}"
    logger.info(
        "convert_to_markdown: original=%r output=%r temp=%r",
        original_name, output_name, temp_name,
    )

    session_dir = TEMP_DIR_BASE / str(uuid.uuid4())
    try:
        session_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Temp dir created: %s", session_dir)
    except OSError as exc:
        logger.exception("Failed to create temp dir %s", session_dir)
        return ConversionResult(
            content="",
            filename=output_name,
            error=f"Internal error: could not create workspace — {exc}",
        )

    try:
        temp_file = session_dir / temp_name
        original_bytes = file_bytes.read()
        file_bytes.seek(0)
        temp_file.write_bytes(original_bytes)
        file_size = temp_file.stat().st_size
        logger.info("Temp file written: %s size=%d bytes", temp_file, file_size)

        if not safe_path(temp_file, session_dir):
            logger.error("Path safety failed: %s outside %s", temp_file, session_dir)
            return ConversionResult(
                content="",
                filename=output_name,
                error="Internal error: path safety validation failed",
            )

        converter = MarkItDown()
        source_path = str(temp_file)
        logger.info("Calling markitdown.convert(%s)", source_path)

        result = converter.convert(source_path)
        raw_text = result.text_content
        logger.info(
            "markitdown result: type=%s text_len=%d text_preview=%r",
            type(result).__name__,
            len(raw_text) if raw_text else 0,
            (raw_text[:80] if raw_text else None),
        )

        if not raw_text or not raw_text.strip():
            logger.warning("markitdown produced empty output for %s (size=%d)", source_path, file_size)
            logger.debug("File bytes hex preview: %s", original_bytes[:32].hex())
            return ConversionResult(
                content="",
                filename=output_name,
                error="Conversion produced empty output — the file may be unreadable or in an unsupported format",
            )

        logger.info("Conversion success: %d chars of markdown", len(raw_text))
        return ConversionResult(content=raw_text, filename=output_name, error=None)

    except (OSError, ValueError, RuntimeError, FileConversionException) as exc:
        logger.exception("Conversion failed for %r: %s", original_name, exc)
        return ConversionResult(
            content="",
            filename=output_name,
            error=f"Conversion failed: {exc}",
        )
    finally:
        shutil.rmtree(session_dir, ignore_errors=True)
        logger.debug("Temp dir cleaned: %s", session_dir)
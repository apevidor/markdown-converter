import logging
import os
import sys
from dataclasses import dataclass, field
from io import BytesIO
from time import time

import streamlit as st

from src.converter import ConversionResult, convert_to_markdown
from src.security import check_file_size, validate_mime

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "DEBUG")),
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("securedoc2md.web")


@dataclass
class RateLimiter:
    max_requests: int = 10
    window_seconds: float = 60.0
    _requests: dict[str, list[float]] = field(default_factory=dict)

    def is_allowed(self, ip: str) -> bool:
        now = time()
        cutoff = now - self.window_seconds
        self._requests.setdefault(ip, [])
        self._requests[ip] = [t for t in self._requests[ip] if t > cutoff]
        if len(self._requests[ip]) >= self.max_requests:
            logger.warning("Rate limit hit: ip=%s count=%d", ip, len(self._requests[ip]))
            return False
        self._requests[ip].append(now)
        return True


HISTORY_KEY = "conversion_history"
MAX_HISTORY = 5


def main() -> None:
    st.set_page_config(page_title="SecureDoc2MD", page_icon="+", layout="wide")
    st.title("SecureDoc2MD")
    st.caption("Convert PDF, DOCX, XLSX to Markdown securely.")

    limiter = _get_rate_limiter()
    client_ip = _get_client_ip()

    uploaded = st.file_uploader(
        "Drop a document here",
        type=["pdf", "docx", "xlsx"],
        accept_multiple_files=False,
    )

    if uploaded is None:
        _render_history()
        return

    logger.info(
        "Upload received: name=%r size=%d ip=%s",
        uploaded.name,
        uploaded.size,
        client_ip,
    )

    if not limiter.is_allowed(client_ip):
        st.error("Too many requests. Please wait before trying again.")
        _render_history()
        return

    raw = uploaded.read()
    buf = BytesIO(raw)

    if not check_file_size(buf):
        st.error("File exceeds the 50MB limit.")
        _render_history()
        return

    if not validate_mime(raw):
        st.error("File type does not match its extension. Rejected for security.")
        _render_history()
        return

    logger.info("Validation passed, starting conversion")

    buf.seek(0)
    with st.spinner("Converting..."):
        progress = st.progress(0)
        result = convert_to_markdown(buf, uploaded.name)
        progress.progress(100)

    logger.info(
        "Conversion result: error=%r content_len=%d filename=%r",
        result.error,
        len(result.content),
        result.filename,
    )

    if result.error is not None:
        st.error(result.error)
    else:
        st.success("Conversion complete!")
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.subheader("Preview")
            st.markdown(result.content)
        with col_b:
            st.download_button(
                label="Download Markdown",
                data=result.content,
                file_name=result.filename,
                mime="text/markdown",
            )
        _add_to_history(uploaded.name, result)

    _render_history()


def _get_rate_limiter() -> RateLimiter:
    if "rate_limiter" not in st.session_state:
        st.session_state["rate_limiter"] = RateLimiter()
    return st.session_state["rate_limiter"]


def _get_client_ip() -> str:
    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        if headers:
            return (
                headers.get("X-Forwarded-For", "127.0.0.1")
                .split(",")[0]
                .strip()
            )
    except (ImportError, ModuleNotFoundError):
        pass
    return "127.0.0.1"


def _add_to_history(name: str, result: ConversionResult) -> None:
    if HISTORY_KEY not in st.session_state:
        st.session_state[HISTORY_KEY] = []
    entry = {
        "original_name": name,
        "output_name": result.filename,
        "content": result.content[:2000],
        "timestamp": time(),
    }
    st.session_state[HISTORY_KEY].insert(0, entry)
    st.session_state[HISTORY_KEY] = st.session_state[HISTORY_KEY][:MAX_HISTORY]


def _render_history() -> None:
    history = st.session_state.get(HISTORY_KEY, [])
    if not history:
        return
    st.divider()
    st.subheader("Recent Conversions")
    for item in history:
        st.caption(f"{item['original_name']} -> {item['output_name']}")


if __name__ == "__main__":
    main()
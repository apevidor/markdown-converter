# run.py - Entry point for SecureDoc2MD with security headers.


from pathlib import Path
import sys

import streamlit.web.bootstrap
from streamlit.web.server import Server
from tornado.web import RequestHandler


def _patch_security_headers() -> None:
    original_prepare = RequestHandler.prepare

    def secure_prepare(self):
        self.set_header("X-Frame-Options", "DENY")
        self.set_header("X-Content-Type-Options", "nosniff")
        self.set_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-eval'",
        )
        original_prepare(self)

    RequestHandler.prepare = secure_prepare  # type: ignore[method-assign]


def main() -> None:
    _patch_security_headers()

    app_path = Path(__file__).resolve().parent / "src" / "web.py"
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.address=0.0.0.0",
        "--server.port=8501",
    ]
    streamlit.web.bootstrap.run(str(app_path), "", [], {})


if __name__ == "__main__":
    main()

"""Browser upload helper for remote noVNC GUI sessions."""

from __future__ import annotations

import argparse
import cgi
import html
import json
import os
import re
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shutil import copyfileobj
from tempfile import NamedTemporaryFile
from typing import BinaryIO

ALLOWED_BOOK_EXTENSIONS = {".pdf", ".txt", ".epub", ".fb2", ".docx"}
DEFAULT_MAX_UPLOAD_BYTES = 1024 * 1024 * 1024
DEFAULT_MARKER_NAME = ".latest_book_upload.json"


def safe_upload_name(filename: str) -> str:
    """Return a safe upload filename while preserving supported book extensions."""
    name = filename.strip().replace("\x00", "").replace("\\", "/").rsplit("/", 1)[-1]
    stem, dot, suffix_part = name.rpartition(".")
    suffix = f".{suffix_part.lower()}" if dot else ""
    if suffix not in ALLOWED_BOOK_EXTENSIONS:
        raise ValueError(f"Unsupported book file type: {suffix or '(none)'}")
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", stem.strip(" ._")).strip(" .")
    if not re.search(r"[A-Za-z0-9]", stem):
        stem = "book"
    return f"{stem}{suffix}"


def unique_upload_path(upload_dir: Path, filename: str) -> Path:
    """Return an unused destination path inside upload_dir."""
    safe_name = safe_upload_name(filename)
    candidate = upload_dir / safe_name
    if not candidate.exists():
        return candidate
    for index in range(1, 10_000):
        candidate = upload_dir / f"{Path(safe_name).stem}_{index}{Path(safe_name).suffix}"
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"Could not allocate upload filename for {safe_name}")


def write_upload_marker(marker_path: Path, uploaded_path: Path) -> None:
    """Write the latest uploaded file path for the GUI process."""
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "path": str(uploaded_path.resolve()),
        "name": uploaded_path.name,
        "uploaded_at": datetime.now(UTC).isoformat(),
    }
    marker_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_upload(field_file: BinaryIO, filename: str, upload_dir: Path, marker_path: Path) -> Path:
    """Save an uploaded book and update the latest-upload marker."""
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = unique_upload_path(upload_dir, filename)
    with NamedTemporaryFile("wb", delete=False, dir=upload_dir, prefix=".upload-", suffix=".tmp") as tmp:
        temp_path = Path(tmp.name)
        copyfileobj(field_file, tmp)
    os.replace(temp_path, destination)
    write_upload_marker(marker_path, destination)
    return destination


def _upload_page(message: str = "") -> bytes:
    message_html = f'<div class="message">{html.escape(message)}</div>' if message else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Books to Audio Upload</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; max-width: 44rem; color: #172033; }}
    form {{ display: grid; gap: 1rem; padding: 1rem; border: 1px solid #d8e0eb; border-radius: 8px; }}
    button {{ width: fit-content; padding: 0.65rem 1rem; font-weight: 700; }}
    .message {{ margin: 1rem 0; padding: 0.75rem; background: #eef8f4; border-radius: 8px; }}
    .hint {{ color: #526174; }}
  </style>
</head>
<body>
  <h1>Books to Audio Upload</h1>
  <p class="hint">
    Upload a TXT, PDF, EPUB, FB2, or DOCX book from this browser.
    The remote GUI will select it automatically.
  </p>
  {message_html}
  <form method="post" action="/upload" enctype="multipart/form-data">
    <input type="file" name="book" accept=".txt,.pdf,.epub,.fb2,.docx" required>
    <button type="submit">Upload book</button>
  </form>
</body>
</html>
""".encode()


def build_handler(
    upload_dir: Path,
    marker_path: Path,
    *,
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
) -> type[BaseHTTPRequestHandler]:
    """Build a request handler bound to upload settings."""

    class UploadHandler(BaseHTTPRequestHandler):
        server_version = "BooksToAudioUpload/1.0"

        def do_GET(self) -> None:  # noqa: N802
            if self.path in {"/", "/upload"}:
                self._send_html(_upload_page())
                return
            if self.path == "/health":
                self._send_text("ok\n")
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/upload":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0:
                self.send_error(HTTPStatus.BAD_REQUEST, "Missing upload body")
                return
            if length > max_upload_bytes:
                self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Upload is too large")
                return

            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                    "CONTENT_LENGTH": str(length),
                },
            )
            field = form["book"] if "book" in form else None
            if field is None or not getattr(field, "filename", "") or field.file is None:
                self.send_error(HTTPStatus.BAD_REQUEST, "Upload field 'book' is required")
                return
            try:
                saved = save_upload(field.file, field.filename, upload_dir, marker_path)
            except ValueError as exc:
                self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            except OSError as exc:
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Could not save upload: {exc}")
                return
            self._send_html(_upload_page(f"Uploaded {saved.name}. The GUI should select it automatically."))

        def log_message(self, _format: str, *_args: object) -> None:
            return

        def _send_html(self, body: bytes) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, text: str) -> None:
            body = text.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return UploadHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve a browser upload page for remote GUI sessions.")
    parser.add_argument("--host", default=os.environ.get("BOOKS_TO_AUDIO_WEB_UPLOAD_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("BOOKS_TO_AUDIO_WEB_UPLOAD_PORT", "6090")))
    parser.add_argument(
        "--upload-dir",
        type=Path,
        default=Path(os.environ.get("BOOKS_TO_AUDIO_WEB_UPLOAD_DIR", "web_uploads")),
    )
    parser.add_argument(
        "--marker",
        type=Path,
        default=(
            Path(os.environ["BOOKS_TO_AUDIO_WEB_UPLOAD_MARKER"])
            if os.environ.get("BOOKS_TO_AUDIO_WEB_UPLOAD_MARKER")
            else None
        ),
    )
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_UPLOAD_BYTES)
    args = parser.parse_args(argv)

    upload_dir = args.upload_dir.resolve()
    marker_path = (args.marker or upload_dir / DEFAULT_MARKER_NAME).resolve()
    handler = build_handler(upload_dir, marker_path, max_upload_bytes=args.max_bytes)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Books-to-Audio upload page: http://{args.host}:{args.port}/upload", flush=True)
    print(f"Uploads directory: {upload_dir}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

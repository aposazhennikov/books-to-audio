from __future__ import annotations

import http.client
import http.server
import json
from io import BytesIO
from pathlib import Path
from threading import Thread

import pytest

from book_normalizer.gui.web_upload_server import (
    build_handler,
    safe_upload_name,
    save_upload,
    unique_upload_path,
)


def test_safe_upload_name_strips_paths_and_replaces_unsafe_characters() -> None:
    assert safe_upload_name(r"C:\fakepath\Моя книга!!.PDF") == "book.pdf"
    assert safe_upload_name("../../chapter one?.epub") == "chapter one_.epub"


def test_safe_upload_name_rejects_unsupported_extensions() -> None:
    with pytest.raises(ValueError, match="Unsupported book file type"):
        safe_upload_name("book.exe")


def test_unique_upload_path_adds_suffix_when_name_exists(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    (upload_dir / "book.txt").write_text("first", encoding="utf-8")

    assert unique_upload_path(upload_dir, "book.txt") == upload_dir / "book_1.txt"


def test_save_upload_writes_file_and_latest_marker(tmp_path: Path) -> None:
    marker_path = tmp_path / "state" / ".latest_book_upload.json"

    saved = save_upload(BytesIO(b"hello book"), "../unsafe name.txt", tmp_path / "uploads", marker_path)

    assert saved == tmp_path / "uploads" / "unsafe name.txt"
    assert saved.read_bytes() == b"hello book"
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    assert marker["path"] == str(saved.resolve())
    assert marker["name"] == "unsafe name.txt"
    assert marker["uploaded_at"]


def test_http_handler_health_and_upload(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    marker_path = tmp_path / ".latest_book_upload.json"
    handler = build_handler(upload_dir, marker_path, max_upload_bytes=1024)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/health")
        response = conn.getresponse()
        assert response.status == 200
        assert response.read() == b"ok\n"
        conn.close()

        boundary = "----books-to-audio-test-boundary"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="book"; filename="remote book.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n"
            "uploaded text\r\n"
            f"--{boundary}--\r\n"
        ).encode()
        conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request(
            "POST",
            "/upload",
            body=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
            },
        )
        response = conn.getresponse()
        response_body = response.read()
        assert response.status == 200
        assert b"Uploaded remote book.txt" in response_body
        assert (upload_dir / "remote book.txt").read_text(encoding="utf-8") == "uploaded text"
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        assert marker["name"] == "remote book.txt"
        conn.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

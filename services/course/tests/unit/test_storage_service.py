from __future__ import annotations

import hashlib

import pytest
from uuid import uuid4

from app.services.storage_service import (
    ALLOWED_TYPES,
    MAGIC_BYTES,
    build_storage_path,
    compute_checksum,
    validate_file_type,
)


class TestValidateFileType:
    """Test file validation logic."""

    def test_valid_pdf(self):
        header = b"%PDF-1.4 test content"
        result = validate_file_type("document.pdf", "application/pdf", header)
        assert result == "pdf"

    def test_valid_txt(self):
        header = b"plain text content"
        result = validate_file_type("notes.txt", "text/plain", header)
        assert result == "txt"

    def test_valid_docx(self):
        header = b"PK\x03\x04" + b"\x00" * 100
        result = validate_file_type(
            "report.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            header,
        )
        assert result == "docx"

    def test_unsupported_extension(self):
        result = validate_file_type("virus.exe", "application/octet-stream", b"data")
        assert result is None

    def test_magic_byte_mismatch(self):
        result = validate_file_type("fake.pdf", "application/pdf", b"NOT-A-PDF content")
        assert result is None

    def test_wrong_mime_type(self):
        result = validate_file_type("notes.txt", "image/png", b"text")
        assert result is None


class TestBuildStoragePath:
    """Test storage path generation."""

    def test_deterministic_path(self):
        cid = uuid4()
        mid = uuid4()
        aid = uuid4()
        path = build_storage_path(cid, mid, aid, "lecture.pdf")
        assert path == f"course-assets/{cid}/{mid}/{aid}/lecture.pdf"

    def test_sanitizes_path_traversal(self):
        cid = uuid4()
        mid = uuid4()
        aid = uuid4()
        path = build_storage_path(cid, mid, aid, "../../evil.pdf")
        assert ".." not in path
        # file_name part should have slashes replaced with underscores and .. stripped
        file_part = path.split(f"{aid}/")[1]
        assert "/" not in file_part


class TestComputeChecksum:
    """Test SHA-256 checksum computation."""

    def test_known_hash(self):
        data = b"test data"
        expected = hashlib.sha256(data).hexdigest()
        assert compute_checksum(data) == expected

    def test_different_data_different_hash(self):
        assert compute_checksum(b"a") != compute_checksum(b"b")

"""Unit tests for ExportService: txt, html, docx, format validation, XSS prevention."""
import uuid
from unittest.mock import MagicMock

import pytest

from app.services.export_service import ExportService


def _make_content(body="Test content body", content_type="listing_description"):
    """Create a mock Content object for export tests."""
    content = MagicMock()
    content.id = uuid.uuid4()
    content.body = body
    content.content_type = content_type
    content.content_metadata = {}
    return content


class TestExportTxt:
    async def test_export_txt(self):
        service = ExportService()
        content = _make_content()
        response = await service.export(content, "txt")
        assert response.media_type == "text/plain"
        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk if isinstance(chunk, bytes) else chunk.encode()
        assert body_bytes == b"Test content body"

    async def test_export_txt_content_disposition(self):
        service = ExportService()
        content = _make_content()
        response = await service.export(content, "txt")
        assert f"content-{content.id}.txt" in response.headers["content-disposition"]


class TestExportHtml:
    async def test_export_html(self):
        service = ExportService()
        content = _make_content()
        response = await service.export(content, "html")
        assert response.media_type == "text/html"
        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk if isinstance(chunk, bytes) else chunk.encode()
        html = body_bytes.decode("utf-8")
        assert "<!DOCTYPE html>" in html
        assert "Test content body" in html

    async def test_export_html_xss_prevention(self):
        service = ExportService()
        content = _make_content(body='<script>alert("xss")</script>')
        response = await service.export(content, "html")
        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk if isinstance(chunk, bytes) else chunk.encode()
        html = body_bytes.decode("utf-8")
        # The <script> tag should be HTML-escaped, not raw
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestExportDocx:
    async def test_export_docx(self):
        service = ExportService()
        content = _make_content()
        response = await service.export(content, "docx")
        assert (
            response.media_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk if isinstance(chunk, bytes) else chunk.encode()
        # DOCX files start with PK (ZIP magic bytes)
        assert body_bytes[:2] == b"PK"


class TestExportValidation:
    async def test_export_invalid_format(self):
        service = ExportService()
        content = _make_content()
        with pytest.raises(ValueError, match="Unsupported format"):
            await service.export(content, "csv")


class TestExportEdgeCases:
    async def test_export_empty_body(self):
        service = ExportService()
        content = _make_content(body="")
        response = await service.export(content, "txt")
        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk if isinstance(chunk, bytes) else chunk.encode()
        assert body_bytes == b""

    async def test_export_unicode_body(self):
        service = ExportService()
        content = _make_content(body="Luxury résidence with café & naïve charm — 日本語テスト")
        response = await service.export(content, "txt")
        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk if isinstance(chunk, bytes) else chunk.encode()
        text = body_bytes.decode("utf-8")
        assert "résidence" in text
        assert "日本語テスト" in text

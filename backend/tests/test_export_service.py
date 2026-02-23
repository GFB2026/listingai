"""Unit tests for ExportService: txt, html, docx, pdf, format validation, XSS prevention."""
import uuid
from unittest.mock import MagicMock, patch

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


class TestExportPdf:
    async def test_export_pdf(self):
        service = ExportService()
        content = _make_content(body="Beautiful oceanfront property.")

        # Mock weasyprint since it may not be installed in test env
        mock_html_cls = MagicMock()
        mock_html_cls.return_value.write_pdf.return_value = b"%PDF-1.4 fake pdf bytes"

        with patch("app.services.export_service.HTML", mock_html_cls, create=True):
            # Patch the import inside _export_pdf
            with patch.dict("sys.modules", {"weasyprint": MagicMock(HTML=mock_html_cls)}):
                response = await service.export(content, "pdf")

        assert response.media_type == "application/pdf"
        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk if isinstance(chunk, bytes) else chunk.encode()
        assert body_bytes == b"%PDF-1.4 fake pdf bytes"

    async def test_export_pdf_xss_safe(self):
        service = ExportService()
        content = _make_content(body='<script>alert("xss")</script>')

        captured_html = {}

        class MockHTML:
            def __init__(self, string=""):
                captured_html["html"] = string

            def write_pdf(self):
                return b"%PDF"

        with patch.dict("sys.modules", {"weasyprint": MagicMock(HTML=MockHTML)}):
            await service.export(content, "pdf")

        # The raw <script> should be escaped
        assert "<script>" not in captured_html["html"]
        assert "&lt;script&gt;" in captured_html["html"]


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

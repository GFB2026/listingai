import io

from fastapi.responses import StreamingResponse

from app.models.content import Content


class ExportService:
    async def export(self, content: Content, format: str) -> StreamingResponse:
        if format == "txt":
            return self._export_txt(content)
        elif format == "html":
            return self._export_html(content)
        elif format == "docx":
            return await self._export_docx(content)
        elif format == "pdf":
            return await self._export_pdf(content)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _export_txt(self, content: Content) -> StreamingResponse:
        buffer = io.BytesIO(content.body.encode("utf-8"))
        return StreamingResponse(
            buffer,
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="content-{content.id}.txt"'},
        )

    def _export_html(self, content: Content) -> StreamingResponse:
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{content.content_type}</title></head>
<body>
<div style="max-width: 800px; margin: 0 auto; font-family: Georgia, serif; padding: 2rem;">
{content.body}
</div>
</body>
</html>"""
        buffer = io.BytesIO(html.encode("utf-8"))
        return StreamingResponse(
            buffer,
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="content-{content.id}.html"'},
        )

    async def _export_docx(self, content: Content) -> StreamingResponse:
        from docx import Document

        doc = Document()
        doc.add_heading(content.content_type.replace("_", " ").title(), level=1)
        for paragraph in content.body.split("\n\n"):
            doc.add_paragraph(paragraph)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="content-{content.id}.docx"'},
        )

    async def _export_pdf(self, content: Content) -> StreamingResponse:
        # PDF export using weasyprint
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
body {{ font-family: Georgia, serif; max-width: 700px; margin: 0 auto; padding: 2rem; }}
h1 {{ color: #1a365d; }}
</style></head>
<body>
<h1>{content.content_type.replace("_", " ").title()}</h1>
<div>{content.body}</div>
</body>
</html>"""

        from weasyprint import HTML

        pdf_bytes = HTML(string=html).write_pdf()
        buffer = io.BytesIO(pdf_bytes)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="content-{content.id}.pdf"'},
        )

# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging
from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile

from odoo import models

_logger = logging.getLogger(__name__)

TEXT_MIMETYPES = {
    "text/plain",
    "text/html",
    "text/csv",
    "text/xml",
    "application/json",
    "application/xml",
}
PDF_MIMETYPES = {"application/pdf"}
IMAGE_MIMETYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
}
AUDIO_MIMETYPES = {
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "audio/mp4",
    "audio/webm",
}
OFFICE_XML_MIMETYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
ODF_MIMETYPES = {
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.presentation",
    "application/vnd.oasis.opendocument.graphics",
}
ZIP_DOC_EXTENSIONS = {"docx", "xlsx", "pptx", "odt", "ods", "odp", "odg"}


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _to_ai_file(self):
        """Convert attachment to provider-agnostic file dict.

        Returns a dict matching the ai_connection 'files' contract:
        {
            "type": "image"|"audio"|"document"|"text",
            "mimetype": str,
            "data": str,       # base64 content or extracted text
            "filename": str,
            "description": str,
        }
        """
        self.ensure_one()
        mimetype = self.mimetype or "application/octet-stream"
        file_type = self._get_ai_file_type(mimetype)

        if file_type in ("image", "audio"):
            data = base64.b64encode(self.raw).decode() if self.raw else ""
        elif file_type in ("text", "document"):
            data = self._extract_text()
        else:
            data = ""

        return {
            "type": file_type,
            "mimetype": mimetype,
            "data": data,
            "filename": self.name or "",
            "description": self.description or "",
        }

    def _get_ai_file_type(self, mimetype):
        if mimetype in IMAGE_MIMETYPES:
            return "image"
        if mimetype in AUDIO_MIMETYPES:
            return "audio"
        if mimetype in PDF_MIMETYPES or mimetype.startswith("video/"):
            return "document"
        if mimetype in TEXT_MIMETYPES:
            return "text"
        if mimetype in OFFICE_XML_MIMETYPES | ODF_MIMETYPES:
            return "text"
        if mimetype == "application/octet-stream" and self.name:
            ext = (self.name or "").rsplit(".", 1)[-1].lower()
            if ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp"):
                return "image"
            if ext in ("mp3", "wav", "ogg", "m4a"):
                return "audio"
            if ext in ("txt", "csv", "json", "xml", "html", "md"):
                return "text"
            if ext in ZIP_DOC_EXTENSIONS:
                return "text"
        return "text"

    def _read_text_content(self):
        try:
            return (self.raw or b"").decode("utf-8", errors="replace")
        except Exception:
            return ""

    def _extract_text(self):
        if self.mimetype in PDF_MIMETYPES:
            return self._extract_pdf_text()
        if self.mimetype in OFFICE_XML_MIMETYPES:
            return self._extract_ooxml_text()
        if self.mimetype in ODF_MIMETYPES:
            return self._extract_odf_text()
        ext = (self.name or "").rsplit(".", 1)[-1].lower()
        if ext in ZIP_DOC_EXTENSIONS:
            return self._extract_zip_xml_text()
        return self._read_text_content()

    def _extract_pdf_text(self):
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(BytesIO(self.raw))
            return "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        except ImportError:
            _logger.warning("PyPDF2 not available, cannot extract PDF text")
            return "[PDF: text extraction requires PyPDF2]"
        except Exception as e:
            _logger.warning("PDF extraction failed: %s", e)
            return "[PDF: extraction failed]"

    def _extract_ooxml_text(self):
        """Extract text from DOCX/XLSX/PPTX (Office Open XML, ZIP-based)."""
        return self._extract_zip_xml_text()

    def _extract_odf_text(self):
        """Extract text from ODT/ODS/ODP (OpenDocument Format, ZIP-based)."""
        return self._extract_zip_xml_text()

    def _extract_zip_xml_text(self):
        """Extract text from XML inside a ZIP archive."""
        try:
            raw = self.raw
            with ZipFile(BytesIO(raw)) as zf:
                for name in zf.namelist():
                    if name.endswith(".xml"):
                        xml_bytes = zf.read(name)
                        tree = ElementTree.fromstring(xml_bytes)
                        texts = tree.itertext()
                        return "\n".join(
                            t.strip() for t in texts if t.strip()
                        )[:10000]
        except Exception as e:
            _logger.warning("ZIP/XML extraction failed for %s: %s", self.name, e)
        return self._read_text_content()

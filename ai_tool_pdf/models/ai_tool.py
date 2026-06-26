from odoo import models
from odoo.addons.ai_tool.tools import aitool


class AiTool(models.Model):
    _inherit = "ai.tool"

    @aitool(
        input_schema={
            "attachment_id": {
                "type": "integer",
                "description": "ID of the PDF attachment",
            },
        },
        output_schema={
            "content": {"type": "string"},
            "filename": {"type": "string"},
        },
    )
    def _ai_read_pdf(self, attachment_id=None):
        att = self.env["ir.attachment"].browse(int(attachment_id or 0))
        if not att:
            return {"error": "Attachment not found"}
        return {
            "content": att._extract_pdf_text()[:10000],
            "filename": att.name or "",
        }

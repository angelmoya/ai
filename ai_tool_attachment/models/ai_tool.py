# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.ai_tool.tools import aitool


class AiTool(models.Model):
    _inherit = "ai.tool"

    @aitool(
        input_schema={
            "attachment_id": {
                "type": "integer",
                "description": "ID of the attachment to read",
            },
            "model": {
                "type": "string",
                "description": "Model to search attachments on",
            },
            "res_id": {
                "type": "integer",
                "description": "Record ID to search attachments on",
            },
        },
        output_schema={
            "attachments": {
                "type": "array",
                "description": "List of attachments found with id, filename, mimetype",
            },
            "count": {"type": "integer"},
        },
    )
    def _ai_read_attachment(self, attachment_id=None, model=None, res_id=None):
        """Find and list attachments on a record. Use format-specific tools
        (read_pdf, read_docx, etc.) to read the actual content."""
        attachments = self.env["ir.attachment"]
        if attachment_id:
            attachments |= attachments.browse(int(attachment_id)).exists()
        if model and res_id:
            attachments |= attachments.search(
                [("res_model", "=", model), ("res_id", "=", int(res_id))]
            )
        results = []
        for att in attachments:
            results.append({
                "id": att.id,
                "filename": att.name or "",
                "mimetype": att.mimetype or "",
                "size": att.file_size or 0,
            })
        return {"attachments": results, "count": len(results)}

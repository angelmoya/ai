from odoo import models
from odoo.addons.ai_tool.tools import aitool


class AiTool(models.Model):
    _inherit = "ai.tool"

    @aitool(
        input_schema={
            "attachment_id": {
                "type": "integer",
                "description": "ID of the image attachment",
            },
        },
        output_schema={
            "mimetype": {"type": "string"},
            "filename": {"type": "string"},
            "size": {"type": "integer"},
        },
    )
    def _ai_read_image(self, attachment_id=None):
        att = self.env["ir.attachment"].browse(int(attachment_id or 0))
        if not att:
            return {"error": "Attachment not found"}
        return {
            "mimetype": att.mimetype or "",
            "filename": att.name or "",
            "size": att.file_size or 0,
        }

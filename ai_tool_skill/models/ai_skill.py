# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

from odoo.addons.ai_tool.tools import aitool


class AiSkill(models.Model):
    _name = "ai.skill"
    _description = "AI Skill"
    _inherits = {"ai.tool": "tool_id"}

    tool_id = fields.Many2one(
        "ai.tool", required=True, ondelete="cascade", auto_join=True
    )
    content = fields.Text(
        required=True,
        help="Detailed instructions and guidelines in Markdown format.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        defaults = {
            "model_id": self.env["ir.model"]._get_id("ai.skill"),
            "function_name": "_ai_get_skill_content",
            "kind": "generic",
        }
        res.update({k: v for k, v in defaults.items() if k in fields_list})
        return res

    @aitool(
        input_schema={},
        output_schema={
            "name": {"type": "string"},
            "content": {"type": "string"},
        },
    )
    def _ai_get_skill_content(self, **kwargs):
        return {
            "name": self.name,
            "content": self.content,
        }

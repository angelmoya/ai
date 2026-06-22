# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AiTool(models.Model):
    _inherit = "ai.tool"

    is_server_action = fields.Boolean()
    server_action_id = fields.Many2one(
        "ir.actions.server",
        string="Server Action",
        domain="[('model_id', '=', model_id)]",
    )

    def _execute_tool(self, *args, record=None, **kwargs):
        self.ensure_one()
        if self.is_server_action and self.server_action_id:
            ctx = {"active_model": record._name if record else self.model_id.model}
            if record:
                ctx["active_id"] = record.id
                ctx["active_ids"] = record.ids
            ctx.update(kwargs)
            result = self.server_action_id.with_context(**ctx).run()
            return result or {}
        return super()._execute_tool(*args, record=record, **kwargs)

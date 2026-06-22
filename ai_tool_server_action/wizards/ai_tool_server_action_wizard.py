# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AiToolServerActionWizard(models.TransientModel):
    _name = "ai.tool.server.action.wizard"
    _description = "Create AI Tool from Server Action"

    server_action_id = fields.Many2one(
        "ir.actions.server",
        string="Server Action",
        required=True,
        domain="[('model_id', '!=', False)]",
    )
    name = fields.Char(required=True)
    description = fields.Text(required=True)
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        related="server_action_id.model_id",
        readonly=True,
    )

    def action_create_tool(self):
        self.ensure_one()
        runner_model = self.env["ir.model"]._get("ai.tool.server.action.runner")
        tool = self.env["ai.tool"].create(
            {
                "name": self.name,
                "description": self.description,
                "model_id": runner_model.id,
                "function_name": "_ai_server_action_wrapper",
                "kind": "generic",
                "is_server_action": True,
                "server_action_id": self.server_action_id.id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "ai.tool",
            "res_id": tool.id,
            "view_mode": "form",
            "target": "current",
        }

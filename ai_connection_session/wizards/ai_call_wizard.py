# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AiCallWizard(models.TransientModel):
    _name = "ai.call.wizard"
    _description = "AI Call Wizard"

    connection_id = fields.Many2one(
        "ai.connection",
        required=True,
        string="Connection",
    )
    session_id = fields.Many2one(
        "ai.connection.session",
        string="Session",
        domain="[('connection_id', '=', connection_id)]",
    )
    prompt = fields.Text(required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get("session_id") and not res.get("connection_id"):
            session = self.env["ai.connection.session"].browse(res["session_id"])
            res["connection_id"] = session.connection_id.id
        return res

    def action_execute(self):
        self.ensure_one()
        call = self.env["ai.connection.call"].create(
            {
                "connection_id": self.connection_id.id,
                "session_id": self.session_id.id if self.session_id else False,
                "prompt": self.prompt,
                "state": "draft",
            }
        )
        call._execute()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ai.connection.call",
            "res_id": call.id,
            "view_mode": "form",
            "target": "current",
        }

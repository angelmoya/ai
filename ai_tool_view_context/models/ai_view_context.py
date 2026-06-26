# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import api, fields, models


class AiViewContext(models.TransientModel):
    _name = "ai.view.context"
    _description = "Current user view context for AI agents"

    user_id = fields.Many2one(
        "res.users", required=True, ondelete="cascade",
        default=lambda self: self.env.uid,
    )
    model = fields.Char()
    view_type = fields.Char()
    domain = fields.Json(default=list)
    record_id = fields.Integer()
    groupby = fields.Json(default=list)
    action_context = fields.Json(default=dict)

    @api.model
    def update_context(self, **kwargs):
        ctx = self.sudo().search(
            [("user_id", "=", self.env.uid)], limit=1, order="id desc"
        )
        vals = {
            "user_id": self.env.uid,
            "model": kwargs.get("model"),
            "view_type": kwargs.get("viewType"),
            "domain": kwargs.get("domain") or [],
            "record_id": kwargs.get("recordId") or 0,
            "groupby": kwargs.get("groupby") or [],
            "action_context": kwargs.get("context") or {},
        }
        if ctx:
            ctx.write(vals)
        else:
            self.sudo().create(vals)

    @api.model
    def get_current_context(self):
        ctx = self.sudo().search(
            [("user_id", "=", self.env.uid)], limit=1, order="id desc"
        )
        if not ctx:
            return {}
        return {
            "model": ctx.model,
            "view_type": ctx.view_type,
            "domain": ctx.domain,
            "record_id": ctx.record_id,
            "groupby": ctx.groupby,
            "context": ctx.action_context,
        }

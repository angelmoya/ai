# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AiConnection(models.Model):
    _inherit = "ai.connection"

    skill_ids = fields.Many2many("ai.skill", string="Skills")
    call_ids = fields.One2many("ai.connection.call", "connection_id", string="Calls")
    call_count = fields.Integer(compute="_compute_call_count")
    session_ids = fields.One2many(
        "ai.connection.session", "connection_id", string="Sessions"
    )
    session_count = fields.Integer(compute="_compute_session_count")
    tool_ids = fields.Many2many(
        "ai.tool",
        string="Available Tools",
        help="Tools available for function calling.",
    )

    def _compute_call_count(self):
        for record in self:
            record.call_count = len(record.call_ids)

    def _compute_session_count(self):
        for record in self:
            record.session_count = len(record.session_ids)

    def action_open_call_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ai.call.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_connection_id": self.id},
        }

    def _get_skills_context(self):
        self.ensure_one()
        if not self.skill_ids:
            return ""
        parts = []
        for skill in self.skill_ids:
            content = skill._get_content()
            if content:
                parts.append(f"## {skill.name}\n\n{content}")
        return "\n\n".join(parts)

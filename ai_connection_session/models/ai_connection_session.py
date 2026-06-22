# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AiConnectionSession(models.Model):
    _name = "ai.connection.session"
    _description = "AI Connection Session"
    _order = "id desc"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    connection_id = fields.Many2one(
        "ai.connection",
        required=True,
        ondelete="cascade",
        string="Connection",
    )
    message_history = fields.Json(string="Message History", default=list)
    message_history_formatted = fields.Text(
        string="Message History (Formatted)",
        compute="_compute_message_history_formatted",
        readonly=True,
    )
    summary = fields.Text(string="Summary")
    call_ids = fields.One2many("ai.connection.call", "session_id", string="Calls")
    call_count = fields.Integer(compute="_compute_call_count", string="Call Count")
    last_call_id = fields.Many2one(
        "ai.connection.call",
        compute="_compute_last_call",
        string="Last Call",
    )

    @api.depends("call_ids")
    def _compute_call_count(self):
        for record in self:
            record.call_count = len(record.call_ids)

    @api.depends("call_ids")
    def _compute_last_call(self):
        for record in self:
            record.last_call_id = record.call_ids[:1].id

    @api.depends("message_history")
    def _compute_message_history_formatted(self):
        for record in self:
            history = record.message_history or []
            if not history:
                record.message_history_formatted = ""
                continue
            parts = []
            for idx, msg in enumerate(history, start=1):
                role = msg.get("role", "unknown")
                name = msg.get("name", "")
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls")
                header = f"[{idx}] {role.upper()}"
                if name:
                    header += f" ({name})"
                parts.append(header)
                parts.append("-" * len(header))
                if content:
                    parts.append(str(content))
                if tool_calls:
                    parts.append("Tool calls:")
                    for tc in tool_calls:
                        tc_name = tc.get("name") or tc.get("function", {}).get("name", "?")
                        parts.append(f"  - {tc_name}: {tc.get('arguments', tc)}")
                parts.append("")
            record.message_history_formatted = "\n".join(parts)

    def action_open_call_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ai.call.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_connection_id": self.connection_id.id,
                "default_session_id": self.id,
            },
        }

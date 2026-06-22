# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AiAgentThread(models.Model):
    _name = "ai.agent.thread"
    _description = "AI Agent Thread"
    _order = "id desc"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    agent_id = fields.Many2one(
        "ai.agent",
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="cascade",
    )
    session_id = fields.Many2one(
        "ai.connection.session",
        string="Connection Session",
        readonly=True,
    )
    message_history = fields.Json(
        string="Message History",
        default=list,
    )
    summary = fields.Text()
    call_ids = fields.One2many(
        "ai.connection.call",
        compute="_compute_call_ids",
        string="Calls",
    )
    call_count = fields.Integer(
        compute="_compute_call_count",
        string="Call Count",
    )
    plan_ids = fields.One2many(
        "ai.agent.plan",
        "thread_id",
        string="Plans",
    )

    @api.depends("session_id.call_ids")
    def _compute_call_ids(self):
        for thread in self:
            if thread.session_id:
                thread.call_ids = thread.session_id.call_ids
            else:
                thread.call_ids = self.env["ai.connection.call"]

    @api.depends("call_ids")
    def _compute_call_count(self):
        for thread in self:
            thread.call_count = len(thread.call_ids)

    def _sync_history_from_call(self, call):
        self.ensure_one()
        history = list(self.message_history or [])
        if call.context:
            history.append({"role": "system", "content": call.context})
        history.append({"role": "user", "content": call.prompt})
        if call.response:
            history.append({"role": "assistant", "content": call.response})
        self.message_history = history

    def action_run_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ai.agent.run.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_agent_id": self.agent_id.id,
                "default_thread_id": self.id,
            },
        }

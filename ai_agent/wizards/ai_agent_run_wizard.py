# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AiAgentRunWizard(models.TransientModel):
    _name = "ai.agent.run.wizard"
    _description = "AI Agent Run Wizard"

    agent_id = fields.Many2one(
        "ai.agent",
        required=True,
    )
    thread_id = fields.Many2one(
        "ai.agent.thread",
        string="Thread",
        domain="[('agent_id', '=', agent_id)]",
    )
    prompt = fields.Text(required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get("agent_id") and not res.get("thread_id"):
            agent = self.env["ai.agent"].browse(res["agent_id"])
            thread = agent._get_or_create_thread(self.env.user)
            res["thread_id"] = thread.id
        return res

    def action_run(self):
        self.ensure_one()
        result = self.agent_id.run(
            prompt=self.prompt,
            thread=self.thread_id,
            user=self.env.user,
        )
        if result._name == "ai.agent.plan":
            return {
                "type": "ir.actions.act_window",
                "res_model": "ai.agent.plan",
                "res_id": result.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "res_model": "ai.connection.call",
            "res_id": result.id,
            "view_mode": "form",
            "target": "current",
        }

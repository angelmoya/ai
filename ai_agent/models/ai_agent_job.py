# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AiAgentJob(models.Model):
    _name = "ai.agent.job"
    _description = "AI Agent Job"
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
        string="Run As",
    )
    trigger_type = fields.Selection(
        [
            ("manual", "Manual"),
            ("scheduled", "Scheduled"),
            ("event", "Event"),
        ],
        default="manual",
        required=True,
    )
    cron_id = fields.Many2one(
        "ir.cron",
        string="Scheduled Action",
        ondelete="set null",
    )
    prompt = fields.Text(required=True)
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("running", "Running"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        default="pending",
        required=True,
    )
    last_result = fields.Text()

    def action_run(self):
        for job in self:
            job.state = "running"
            try:
                agent = job.agent_id
                thread = agent._get_or_create_thread(job.user_id)
                result = agent.run(prompt=job.prompt, thread=thread, user=job.user_id)
                job.last_result = getattr(result, "response", str(result))
                job.state = "done"
            except Exception as e:
                job.last_result = str(e)
                job.state = "error"
                raise

    def action_reset(self):
        for job in self:
            job.state = "pending"
            job.last_result = False

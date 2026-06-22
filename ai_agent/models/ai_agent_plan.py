# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AiAgentPlan(models.Model):
    _name = "ai.agent.plan"
    _description = "AI Agent Plan"
    _order = "id desc"

    name = fields.Char(
        compute="_compute_name",
        store=True,
    )
    agent_id = fields.Many2one(
        "ai.agent",
        required=True,
        ondelete="cascade",
    )
    thread_id = fields.Many2one(
        "ai.agent.thread",
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="cascade",
    )
    goal = fields.Text(required=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending_approval", "Pending Approval"),
            ("running", "Running"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
    )
    requires_approval = fields.Boolean(default=True)
    step_ids = fields.One2many(
        "ai.agent.plan.step",
        "plan_id",
        string="Steps",
    )

    @api.depends("agent_id", "goal")
    def _compute_name(self):
        for plan in self:
            plan.name = f"{plan.agent_id.name}: {plan.goal[:50]}"

    def action_approve(self):
        for plan in self:
            if plan.state == "pending_approval":
                plan.state = "running"
                plan.action_execute()

    def action_reject(self):
        for plan in self:
            if plan.state in ("draft", "pending_approval"):
                plan.state = "error"

    def action_execute(self):
        for plan in self:
            plan.state = "running"
            try:
                for step in plan.step_ids.sorted("sequence"):
                    if step.state in ("done", "skipped"):
                        continue
                    step.action_execute()
                plan.state = "done"
            except Exception:
                plan.state = "error"
                raise


class AiAgentPlanStep(models.Model):
    _name = "ai.agent.plan.step"
    _description = "AI Agent Plan Step"
    _order = "sequence, id"

    plan_id = fields.Many2one(
        "ai.agent.plan",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    description = fields.Text(required=True)
    tool_id = fields.Many2one(
        "ai.tool",
        string="Tool",
    )
    connection_id = fields.Many2one(
        "ai.connection",
        string="Connection",
    )
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("running", "Running"),
            ("done", "Done"),
            ("skipped", "Skipped"),
            ("error", "Error"),
        ],
        default="pending",
        required=True,
    )
    result = fields.Text()
    auto_executable = fields.Boolean(default=True)

    def action_execute(self):
        self.ensure_one()
        self.state = "running"
        try:
            agent = self.plan_id.agent_id
            connection = self.connection_id or agent._select_connection(
                self.description
            )
            system_prompt = agent._build_system_prompt()
            call = self.env["ai.connection.call"].create(
                {
                    "connection_id": connection.id,
                    "session_id": self.plan_id.thread_id.session_id.id
                    if self.plan_id.thread_id and self.plan_id.thread_id.session_id
                    else False,
                    "prompt": self.description,
                    "context": system_prompt,
                    "state": "draft",
                }
            )
            call._execute()
            self.result = call.response
            self.state = "done"
        except Exception as e:
            self.result = str(e)
            self.state = "error"
            raise

    def action_skip(self):
        for step in self:
            step.state = "skipped"

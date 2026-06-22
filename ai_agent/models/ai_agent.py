# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AiAgent(models.Model):
    _name = "ai.agent"
    _description = "AI Agent"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    goal = fields.Text()
    soul_id = fields.Many2one(
        "ai.agent.soul",
        string="Soul",
    )
    protocol_ids = fields.Many2many(
        "ai.agent.protocol",
        string="Protocols",
    )
    skill_ids = fields.Many2many(
        "ai.skill",
        string="Skills",
    )
    tool_ids = fields.Many2many(
        "ai.tool",
        string="Tools",
    )
    connection_id = fields.Many2one(
        "ai.connection",
        string="Default Connection",
        required=True,
    )
    connection_ids = fields.Many2many(
        "ai.connection",
        "ai_agent_connection_rel",
        "agent_id",
        "connection_id",
        string="Allowed Connections",
    )
    connection_rule_ids = fields.One2many(
        "ai.agent.connection.rule",
        "agent_id",
        string="Connection Rules",
    )
    planning_enabled = fields.Boolean(
        default=False,
        string="Enable Planning",
    )
    plan_requires_approval = fields.Boolean(
        default=True,
        string="Plans Require Approval",
    )
    thread_ids = fields.One2many(
        "ai.agent.thread",
        "agent_id",
        string="Threads",
    )
    thread_count = fields.Integer(
        compute="_compute_thread_count",
        string="Thread Count",
    )
    job_ids = fields.One2many(
        "ai.agent.job",
        "agent_id",
        string="Jobs",
    )
    job_count = fields.Integer(
        compute="_compute_job_count",
        string="Job Count",
    )

    @api.depends("thread_ids")
    def _compute_thread_count(self):
        for agent in self:
            agent.thread_count = len(agent.thread_ids)

    @api.depends("job_ids")
    def _compute_job_count(self):
        for agent in self:
            agent.job_count = len(agent.job_ids)

    def _build_system_prompt(self):
        self.ensure_one()
        parts = []
        if self.goal:
            parts.append(f"# Goal\n\n{self.goal}")
        if self.soul_id:
            soul = self.soul_id
            soul_parts = []
            if soul.personality:
                soul_parts.append(f"Personality: {soul.personality}")
            if soul.voice_guidelines:
                soul_parts.append(f"Voice: {soul.voice_guidelines}")
            if soul.values:
                soul_parts.append(f"Values: {soul.values}")
            if soul.fallback_behavior:
                soul_parts.append(f"Fallback: {soul.fallback_behavior}")
            if soul_parts:
                parts.append("# Soul\n\n" + "\n\n".join(soul_parts))
        protocol_prompts = self.protocol_ids.filtered(
            lambda p: p.protocol_type == "prompt" and p.content
        )
        if protocol_prompts:
            parts.append(
                "# Protocols\n\n"
                + "\n\n".join(f"- {p.name}: {p.content}" for p in protocol_prompts)
            )
        if self.skill_ids:
            skill_parts = []
            for skill in self.skill_ids:
                content = skill._get_content()
                if content:
                    skill_parts.append(f"## {skill.name}\n\n{content}")
            if skill_parts:
                parts.append("# Skills\n\n" + "\n\n".join(skill_parts))
        return "\n\n".join(parts)

    def _get_or_create_thread(self, user):
        self.ensure_one()
        thread = self.env["ai.agent.thread"].search(
            [
                ("agent_id", "=", self.id),
                ("user_id", "=", user.id),
                ("active", "=", True),
            ],
            limit=1,
            order="id desc",
        )
        if not thread:
            thread = self.env["ai.agent.thread"].create(
                {
                    "name": f"{self.name} - {user.name}",
                    "agent_id": self.id,
                    "user_id": user.id,
                }
            )
        return thread

    def _select_connection(self, task_description=""):
        self.ensure_one()
        for rule in self.connection_rule_ids.filtered("active"):
            if rule.condition and rule.condition.lower() in (task_description or "").lower():
                return rule.connection_id
        return self.connection_id

    def _get_available_tools(self):
        self.ensure_one()
        return self.tool_ids

    def run(self, prompt, thread=None, user=None, record=None):
        self.ensure_one()
        if not user:
            user = self.env.user
        if not thread:
            thread = self._get_or_create_thread(user)
        if self.planning_enabled:
            return self._plan_and_run(prompt, thread, user, record)
        return self._run_prompt(prompt, thread, user, record)

    def _run_prompt(self, prompt, thread, user, record=None):
        self.ensure_one()
        connection = self._select_connection(prompt)
        system_prompt = self._build_system_prompt()
        call = self.env["ai.connection.call"].create(
            {
                "connection_id": connection.id,
                "session_id": thread.session_id.id if thread.session_id else False,
                "prompt": prompt,
                "context": system_prompt,
                "state": "draft",
            }
        )
        call._execute()
        if thread.session_id:
            thread.message_history = thread.session_id.message_history
        else:
            thread._sync_history_from_call(call)
        return call

    def _plan_and_run(self, prompt, thread, user, record=None):
        self.ensure_one()
        plan = self._plan(prompt, thread, user)
        if plan.requires_approval and plan.state == "pending_approval":
            return plan
        plan.action_execute()
        return plan

    def _plan(self, prompt, thread, user):
        self.ensure_one()
        plan = self.env["ai.agent.plan"].create(
            {
                "agent_id": self.id,
                "thread_id": thread.id,
                "user_id": user.id,
                "goal": prompt,
                "state": "draft",
                "requires_approval": self.plan_requires_approval,
            }
        )
        # Generate steps via the default connection with a planning prompt
        connection = self.connection_id
        plan_prompt = self._build_planning_prompt(prompt)
        result = connection._run(plan_prompt, tools=None)
        steps = self._parse_plan(result)
        for idx, step_data in enumerate(steps, start=1):
            self.env["ai.agent.plan.step"].create(
                {
                    "plan_id": plan.id,
                    "sequence": idx,
                    "description": step_data.get("description", ""),
                    "auto_executable": step_data.get("auto_executable", True),
                }
            )
        plan.state = "pending_approval" if plan.requires_approval else "running"
        return plan

    def _build_planning_prompt(self, prompt):
        self.ensure_one()
        tools_text = "\n".join(f"- {tool.name}: {tool.description}" for tool in self.tool_ids)
        return (
            "You are a planning assistant. Given the user request, break it into a list of steps. "
            "Each step must be a JSON object with 'description' and optionally 'auto_executable' (boolean). "
            "Return a JSON array of steps.\n\n"
            f"Available tools:\n{tools_text}\n\n"
            f"User request: {prompt}"
        )

    def _parse_plan(self, result):
        try:
            data = json.loads(result)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "steps" in data:
                return data["steps"]
        except json.JSONDecodeError:
            pass
        # Fallback: treat each non-empty line as a step
        return [
            {"description": line.strip(), "auto_executable": True}
            for line in (result or "").splitlines()
            if line.strip()
        ]

    def action_open_threads(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ai.agent.thread",
            "view_mode": "list,form",
            "domain": [("agent_id", "=", self.id)],
            "context": {"default_agent_id": self.id},
        }

    def action_open_jobs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ai.agent.job",
            "view_mode": "list,form",
            "domain": [("agent_id", "=", self.id)],
            "context": {"default_agent_id": self.id},
        }

    def action_run_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ai.agent.run.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_agent_id": self.id},
        }

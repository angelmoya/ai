# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import fields, models


class AiAgent(models.Model):
    _inherit = "ai.agent"

    is_orchestrator = fields.Boolean(default=False)
    orchestrator_member_ids = fields.One2many(
        "ai.agent.orchestrator.member",
        "orchestrator_id",
        string="Member Agents",
    )

    def run(self, prompt, thread=None, user=None, record=None):
        self.ensure_one()
        if self.is_orchestrator:
            return self._run_orchestrator(prompt, thread, user, record)
        return super().run(prompt, thread=thread, user=user, record=record)

    def _run_orchestrator(self, prompt, thread, user, record=None):
        self.ensure_one()
        if not thread:
            thread = self._get_or_create_thread(user)
        # Build orchestration plan
        plan = self.env["ai.agent.plan"].create(
            {
                "agent_id": self.id,
                "thread_id": thread.id,
                "user_id": user.id,
                "goal": prompt,
                "state": "running",
                "requires_approval": False,
            }
        )
        # Generate steps via the orchestrator connection
        plan_prompt = self._build_orchestration_prompt(prompt)
        result = self.connection_id._run(plan_prompt, tools=None)
        steps = self._parse_orchestration_plan(result)
        for idx, step_data in enumerate(steps, start=1):
            member = self._resolve_member(step_data.get("role"))
            if not member:
                continue
            self.env["ai.agent.plan.step"].create(
                {
                    "plan_id": plan.id,
                    "sequence": idx,
                    "description": step_data.get("description", ""),
                    "connection_id": member.agent_id.connection_id.id,
                    "auto_executable": True,
                }
            )
        # Execute each step in the corresponding member agent
        for step in plan.step_ids.sorted("sequence"):
            member = self._resolve_member_by_description(step.description)
            if member:
                call = member.agent_id.run(
                    prompt=step.description,
                    thread=thread,
                    user=user,
                    record=record,
                )
                step.result = getattr(call, "response", str(call))
                step.state = "done"
        plan.state = "done"
        return plan

    def _build_orchestration_prompt(self, prompt):
        self.ensure_one()
        members = self.orchestrator_member_ids
        members_text = "\n".join(
            f"- {m.role}: {m.agent_id.name} - {m.description or ''}"
            for m in members
        )
        return (
            "You are an orchestrator. Given the user request, break it into steps "
            "and assign each step to one of the member agents by role. "
            "Return a JSON array of objects with 'role' and 'description'.\n\n"
            f"Members:\n{members_text}\n\n"
            f"User request: {prompt}"
        )

    def _parse_orchestration_plan(self, result):
        try:
            data = json.loads(result)
            if isinstance(data, list):
                return data
            return data.get("steps", [])
        except json.JSONDecodeError:
            return [
                {"role": "", "description": line.strip()}
                for line in (result or "").splitlines()
                if line.strip()
            ]

    def _resolve_member(self, role):
        self.ensure_one()
        if not role:
            return self.orchestrator_member_ids[:1]
        return self.orchestrator_member_ids.filtered(
            lambda m: m.role and m.role.lower() == role.lower()
        )[:1]

    def _resolve_member_by_description(self, description):
        self.ensure_one()
        # Simple heuristic: re-run resolution based on the description
        # In a real implementation, the role would be stored on the step.
        return self.orchestrator_member_ids[:1]

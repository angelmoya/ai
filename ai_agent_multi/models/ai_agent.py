# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import AccessError


class AiAgent(models.Model):
    _inherit = "ai.agent"

    access_rule_ids = fields.One2many(
        "ai.agent.access.rule",
        "agent_id",
        string="Access Rules",
    )

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, **kwargs):
        if self.env.is_system():
            return super()._search(
                args, offset=offset, limit=limit, order=order, **kwargs
            )
        allowed_agent_ids = self._get_allowed_agent_ids()
        if allowed_agent_ids is None:
            # No access rules defined: agent module behavior remains unrestricted.
            return super()._search(
                args, offset=offset, limit=limit, order=order, **kwargs
            )
        # Agents without rules remain visible; agents with rules require explicit
        # access.
        agents_with_rules = (
            self.env["ai.agent.access.rule"].sudo().search([]).mapped("agent_id").ids
        )
        domain = [
            "|",
            ("id", "not in", agents_with_rules),
            ("id", "in", allowed_agent_ids),
        ]
        return super()._search(
            args + domain, offset=offset, limit=limit, order=order, **kwargs
        )

    def _get_allowed_agent_ids(self, user=None):
        if not user:
            user = self.env.user
        all_rules = self.env["ai.agent.access.rule"].sudo().search([])
        if not all_rules:
            return None
        rules = all_rules.filtered(
            lambda r, user=user: r.user_id == user
            or (r.group_id and r.group_id in user.groups_id)
        )
        return rules.mapped("agent_id").ids

    def _check_access(self, user=None):
        """Raise AccessError if the given user cannot use this agent."""
        if not self:
            return
        self.ensure_one()
        if self.env.is_system():
            return
        if not user:
            user = self.env.user
        if self.id not in self._get_allowed_agent_ids(user):
            raise AccessError(
                self.env._("You are not allowed to use agent '%s'.", self.name)
            )

    def _get_or_create_thread(self, user):
        self._check_access(user)
        return super()._get_or_create_thread(user)

    def run(self, prompt, thread=None, user=None, record=None):
        if not user:
            user = self.env.user
        self._check_access(user)
        return super().run(prompt, thread=thread, user=user, record=record)

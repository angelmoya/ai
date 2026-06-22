# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AiAgent(models.Model):
    _inherit = "ai.agent"

    access_rule_ids = fields.One2many(
        "ai.agent.access.rule",
        "agent_id",
        string="Access Rules",
    )

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self.env.is_system():
            return super()._search(
                args, offset=offset, limit=limit, order=order, count=count,
                access_rights_uid=access_rights_uid,
            )
        allowed_agent_ids = self._get_allowed_agent_ids()
        domain = [("id", "in", allowed_agent_ids)]
        return super()._search(
            args + domain, offset=offset, limit=limit, order=order, count=count,
            access_rights_uid=access_rights_uid,
        )

    def _get_allowed_agent_ids(self):
        user = self.env.user
        rules = self.env["ai.agent.access.rule"].search(
            ["|", ("user_id", "=", user.id), ("group_id", "in", user.groups_id.ids)]
        )
        return rules.mapped("agent_id").ids

    def _check_access(self, user=None):
        self.ensure_one()
        if self.env.is_system():
            return True
        if not user:
            user = self.env.user
        return self.id in self._get_allowed_agent_ids()

    def _get_or_create_thread(self, user):
        if not self._check_access(user):
            self.env["ai.agent.thread"].check_access_rights("create")
        return super()._get_or_create_thread(user)

    def run(self, prompt, thread=None, user=None, record=None):
        if not user:
            user = self.env.user
        if not self._check_access(user):
            self.check_access_rights("write")
        return super().run(prompt, thread=thread, user=user, record=record)

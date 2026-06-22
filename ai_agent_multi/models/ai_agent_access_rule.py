# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AiAgentAccessRule(models.Model):
    _name = "ai.agent.access.rule"
    _description = "AI Agent Access Rule"

    agent_id = fields.Many2one(
        "ai.agent",
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        "res.users",
        ondelete="cascade",
    )
    group_id = fields.Many2one(
        "res.groups",
        ondelete="cascade",
    )

    _sql_constraints = [
        (
            "check_user_or_group",
            "CHECK(user_id IS NOT NULL OR group_id IS NOT NULL)",
            "An access rule must reference a user or a group.",
        ),
    ]

# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AiAgentConnectionRule(models.Model):
    _name = "ai.agent.connection.rule"
    _description = "AI Agent Connection Rule"
    _order = "sequence, id"

    agent_id = fields.Many2one(
        "ai.agent",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    condition = fields.Char(
        help="Simple keyword or expression used to decide if this rule matches a task.",
    )
    connection_id = fields.Many2one(
        "ai.connection",
        required=True,
        string="Connection",
    )
    active = fields.Boolean(default=True)

# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AiAgentOrchestratorMember(models.Model):
    _name = "ai.agent.orchestrator.member"
    _description = "AI Agent Orchestrator Member"
    _order = "sequence, id"

    orchestrator_id = fields.Many2one(
        "ai.agent",
        required=True,
        ondelete="cascade",
        domain="[('is_orchestrator', '=', True)]",
    )
    agent_id = fields.Many2one(
        "ai.agent",
        required=True,
        ondelete="cascade",
    )
    role = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    description = fields.Text()

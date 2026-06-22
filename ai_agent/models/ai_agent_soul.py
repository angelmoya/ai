# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AiAgentSoul(models.Model):
    _name = "ai.agent.soul"
    _description = "AI Agent Soul"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    personality = fields.Text()
    voice_guidelines = fields.Text()
    values = fields.Text()
    fallback_behavior = fields.Text()

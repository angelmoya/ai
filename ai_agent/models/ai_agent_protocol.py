# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AiAgentProtocol(models.Model):
    _name = "ai.agent.protocol"
    _description = "AI Agent Protocol"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    protocol_type = fields.Selection(
        [
            ("prompt", "System Prompt Rule"),
            ("tool_filter", "Tool Filter"),
            ("pre_tool_check", "Pre-execution Check"),
            ("post_tool_check", "Post-execution Check"),
        ],
        default="prompt",
        required=True,
    )
    condition = fields.Char()
    action = fields.Selection(
        [
            ("allow", "Allow"),
            ("block", "Block"),
            ("confirm", "Require Confirmation"),
            ("log", "Log Only"),
        ],
        default="allow",
        required=True,
    )
    message = fields.Text()
    content = fields.Text(
        string="Protocol Content",
        help="Text injected into the system prompt or used by code-level checks.",
    )

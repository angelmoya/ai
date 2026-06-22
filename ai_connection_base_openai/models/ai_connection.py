# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from ..client import AiConnectionOpenAIClient


class AiConnection(models.Model):
    _inherit = "ai.connection"

    kind = fields.Selection(
        selection_add=[("base_openai", "OpenAI-compatible")],
        ondelete={"base_openai": "cascade"},
    )
    api_key = fields.Char(
        groups="base.group_system",
        help="API key for authentication with the provider.",
    )
    max_tokens = fields.Integer(
        default=2048,
        help="Maximum number of tokens in the response.",
    )
    temperature = fields.Float(
        default=0.7,
        help="Sampling temperature for the model.",
    )

    def _get_client_base_openai(self, tools):
        self.ensure_one()
        return AiConnectionOpenAIClient(
            tools=tools,
            endpoint=self.url,
            api_key=self.api_key,
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

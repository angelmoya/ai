# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from ..client import AiConnectionOllamaClient


class AiConnection(models.Model):
    _inherit = "ai.connection"

    kind = fields.Selection(
        selection_add=[("ollama", "Ollama")],
        ondelete={"ollama": "cascade"},
    )
    ollama_options = fields.Json(
        help="Additional Ollama options like num_ctx, num_predict, etc.",
    )

    def _get_client_ollama(self, tools):
        self.ensure_one()
        return AiConnectionOllamaClient(
            tools=tools,
            endpoint=self.url or "http://localhost:11434",
            api_key=self.api_key,
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            ollama_options=self.ollama_options,
        )

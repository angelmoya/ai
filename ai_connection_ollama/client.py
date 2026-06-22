# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.ai_connection_base_openai.client import AiConnectionOpenAIClient


class AiConnectionOllamaClient(AiConnectionOpenAIClient):
    """Ollama-specific client that injects ollama_options into the payload."""

    def __init__(self, ollama_options=None, **kwargs):
        super().__init__(**kwargs)
        self.ollama_options = ollama_options or {}

    def _enrich_payload(self, payload):
        payload = super()._enrich_payload(payload)
        if self.ollama_options:
            payload["options"] = self.ollama_options
        return payload

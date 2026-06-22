# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging

import requests

from odoo.addons.ai_connection.client import AiConnectionClient

_logger = logging.getLogger(__name__)


class AiConnectionOpenAIClient(AiConnectionClient):
    """OpenAI-compatible chat completions client.

    Implements the /v1/chat/completions protocol used by OpenAI,
    Ollama, vLLM, Together, Groq, and many other providers.
    """

    def __init__(
        self,
        tools=None,
        endpoint=None,
        api_key=None,
        model=None,
        max_tokens=2048,
        temperature=0.7,
    ):
        super().__init__()
        self.tools = tools
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    def handle_message(self, messages=None, **kwargs):
        payload = self._build_payload(messages)
        payload = self._enrich_payload(payload)
        raw = self._send_request(payload)
        return self._parse_response(raw)

    def _build_payload(self, messages):
        payload = {
            "model": self.model,
            "messages": messages or [],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        if self.tools:
            payload["tools"] = self._get_tools_schema()
        return payload

    def _enrich_payload(self, payload):
        """Hook for subclasses to add provider-specific fields.

        Override to inject extra payload keys (e.g. ollama_options).
        """
        return payload

    def _get_tools_schema(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool._get_tool_definition()["inputSchema"],
                },
            }
            for tool in self.tools
        ]

    def _get_headers(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _send_request(self, payload):
        if not self.endpoint:
            raise ValueError("No endpoint configured for AI connection")
        url = self.endpoint.rstrip("/") + "/chat/completions"
        response = requests.post(
            url,
            json=payload,
            headers=self._get_headers(),
            timeout=120,
        )
        response.raise_for_status()
        return response.json()

    def _parse_response(self, data):
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        result = {
            "message": {
                "role": message.get("role", "assistant"),
                "content": message.get("content", ""),
            },
            "usage": data.get("usage", {}),
            "model": data.get("model"),
        }
        tool_calls = message.get("tool_calls")
        if tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": json.loads(tc["function"]["arguments"]),
                    },
                }
                for tc in tool_calls
            ]
        return result

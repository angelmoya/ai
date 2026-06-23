# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestOllamaConnection(TransactionCase):
    def setUp(self):
        super().setUp()
        self.connection = self.env["ai.connection"].create(
            {
                "name": "Test Ollama",
                "kind": "ollama",
                "url": "http://localhost:11434",
                "model": "llama3",
            }
        )

    def test_ollama_kind_registered(self):
        self.assertEqual(self.connection.kind, "ollama")

    def test_ollama_options_field(self):
        self.connection.ollama_options = {"num_ctx": 4096}
        self.assertEqual(self.connection.ollama_options, {"num_ctx": 4096})

    def test_ollama_run(self):
        fake_response = {
            "message": {
                "role": "assistant",
                "content": "Hello from Ollama!",
            },
            "prompt_eval_count": 10,
            "eval_count": 5,
        }
        with patch(
            "odoo.addons.ai_connection_ollama.models.ai_connection.OllamaClient.chat",
            return_value=fake_response,
        ):
            result = self.connection._run("Hi")
        self.assertEqual(result[0], "Hello from Ollama!")

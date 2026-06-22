# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestAiConnectionOllama(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.connection = cls.env["ai.connection"].create(
            {
                "name": "Test Ollama",
                "kind": "ollama",
                "model": "llama3",
            }
        )

    def test_kind_selection_added(self):
        types = self.env["ai.connection"].fields_get(["kind"])
        selection = types["kind"].get("selection")
        self.assertTrue(any(s[0] == "ollama" for s in selection))

    def test_default_endpoint(self):
        client = self.connection._get_client_ollama([])
        self.assertEqual(client.endpoint, "http://localhost:11434")

    def test_custom_endpoint(self):
        self.connection.url = "http://192.168.1.100:11434"
        client = self.connection._get_client_ollama([])
        self.assertEqual(client.endpoint, "http://192.168.1.100:11434")

    def test_ollama_options_injected(self):
        self.connection.ollama_options = {"num_ctx": 4096, "num_predict": 128}
        client = self.connection._get_client_ollama([])
        payload = client._build_payload([{"role": "user", "content": "Hi"}])
        self.assertEqual(payload["options"], {"num_ctx": 4096, "num_predict": 128})

    def test_no_ollama_options(self):
        client = self.connection._get_client_ollama([])
        payload = client._build_payload([{"role": "user", "content": "Hi"}])
        self.assertNotIn("options", payload)

    def test_execution_via_ollama(self):
        mock_response = {
            "choices": [{"message": {"content": "LLaMA response"}}],
            "usage": {"prompt_tokens": 15, "completion_tokens": 8},
            "model": "llama3",
        }
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            result = self.connection._run("Hello llama")

        self.assertEqual(result, "LLaMA response")
        call_args = mock_post.call_args
        self.assertIn("11434/v1/chat/completions", call_args[0][0])

    def test_demo_data_loaded(self):
        demo = self.env.ref(
            "ai_connection_ollama.ollama_default", raise_if_not_found=False
        )
        self.assertTrue(demo)
        self.assertEqual(demo.kind, "ollama")
        self.assertEqual(demo.model, "llama3")

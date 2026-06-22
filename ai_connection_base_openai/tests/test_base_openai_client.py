# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.ai_connection.client import AiConnectionClient

from ..client import AiConnectionOpenAIClient


class TestAiConnectionBaseOpenAIClient(TransactionCase):
    def setUp(self):
        super().setUp()
        self.tool_model = self.env["ir.model"].search(
            [("model", "=", "ai.tool")], limit=1
        )
        self.connection = self.env["ai.connection"].create(
            {
                "name": "Test Base OpenAI",
                "kind": "base_openai",
                "url": "https://api.openai.com/v1",
                "model": "gpt-4o",
                "api_key": "test-key",
                "max_tokens": 2048,
                "temperature": 0.7,
            }
        )

    def test_kind_selection_added(self):
        types = self.env["ai.connection"].fields_get(["kind"])
        selection = types["kind"].get("selection")
        self.assertTrue(any(s[0] == "base_openai" for s in selection))

    def test_client_instantiation(self):
        client = self.connection._get_client_base_openai([])
        self.assertIsInstance(client, AiConnectionClient)
        self.assertIsInstance(client, AiConnectionOpenAIClient)
        self.assertEqual(client.endpoint, "https://api.openai.com/v1")
        self.assertEqual(client.api_key, "test-key")
        self.assertEqual(client.model, "gpt-4o")

    def test_handle_message_without_tools(self):
        client = self.connection._get_client_base_openai([])
        mock_response = {
            "choices": [{"message": {"role": "assistant", "content": "Hello!"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "model": "gpt-4o",
        }
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            result = client.handle_message(messages=[{"role": "user", "content": "Hi"}])

        self.assertEqual(result["message"]["content"], "Hello!")
        self.assertEqual(result["usage"]["prompt_tokens"], 10)
        self.assertEqual(result["model"], "gpt-4o")
        self.assertNotIn("tool_calls", result)

    def test_handle_message_with_tool_calls(self):
        mock_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_abc",
                                "type": "function",
                                "function": {
                                    "name": "get_date",
                                    "arguments": "{}",
                                },
                            }
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 15, "completion_tokens": 3},
            "model": "gpt-4o",
        }
        client = self.connection._get_client_base_openai([])
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            result = client.handle_message(
                messages=[{"role": "user", "content": "What's the date?"}]
            )

        self.assertIn("tool_calls", result)
        self.assertEqual(len(result["tool_calls"]), 1)
        tc = result["tool_calls"][0]
        self.assertEqual(tc["id"], "call_abc")
        self.assertEqual(tc["function"]["name"], "get_date")
        self.assertEqual(tc["function"]["arguments"], {})

    def test_enrich_payload_hook(self):
        class CustomClient(AiConnectionOpenAIClient):
            def _enrich_payload(self, payload):
                payload["options"] = {"num_ctx": 4096}
                return payload

        client = CustomClient(
            tools=[],
            endpoint="http://localhost:11434/v1",
            model="llama3",
        )
        payload = client._build_payload([{"role": "user", "content": "Hi"}])
        self.assertEqual(payload["options"], {"num_ctx": 4096})

    def test_headers_with_api_key(self):
        client = AiConnectionOpenAIClient(
            api_key="sk-test",
        )
        headers = client._get_headers()
        self.assertEqual(headers["Authorization"], "Bearer sk-test")

    def test_headers_without_api_key(self):
        client = AiConnectionOpenAIClient()
        headers = client._get_headers()
        self.assertNotIn("Authorization", headers)

    def test_send_request_no_endpoint(self):
        client = AiConnectionOpenAIClient(model="gpt-4")
        with self.assertRaises(ValueError):
            client._send_request({"model": "gpt-4"})

    def test_execute_via_connection(self):
        mock_response = {
            "choices": [{"message": {"content": "Hello back!"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "model": "gpt-4o",
        }
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            result = self.connection._run("Hello")

        self.assertEqual(result, "Hello back!")

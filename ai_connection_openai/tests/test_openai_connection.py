# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestAiConnectionOpenAI(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.connection = cls.env["ai.connection"].create(
            {
                "name": "Test OpenAI",
                "kind": "openai",
                "url": "https://api.openai.com/v1",
                "model": "gpt-4o",
                "api_key": "test-key",
            }
        )

    def test_kind_selection_added(self):
        types = self.env["ai.connection"].fields_get(["kind"])
        selection = types["kind"].get("selection")
        self.assertTrue(any(s[0] == "openai" for s in selection))

    def test_get_client_openai(self):
        client = self.connection._get_client_openai([])
        self.assertEqual(client.endpoint, "https://api.openai.com/v1")
        self.assertEqual(client.api_key, "test-key")
        self.assertEqual(client.model, "gpt-4o")

    def test_execution_via_openai(self):
        mock_response = {
            "choices": [{"message": {"content": "OpenAI response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "model": "gpt-4o",
        }
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            result = self.connection._run("Hello")

        self.assertEqual(result, "OpenAI response")
        call_args = mock_post.call_args
        self.assertIn("api.openai.com", call_args[0][0])

    def test_demo_data_loaded(self):
        demo = self.env.ref(
            "ai_connection_openai.openai_default", raise_if_not_found=False
        )
        self.assertTrue(demo)
        self.assertEqual(demo.kind, "openai")
        self.assertEqual(demo.model, "gpt-4o")

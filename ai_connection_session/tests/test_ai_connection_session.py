# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestAiConnectionSession(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.connection = cls.env["ai.connection"].create(
            {
                "name": "Test Connection",
                "kind": "base_openai",
                "url": "https://api.openai.com/v1",
                "model": "gpt-4o",
                "api_key": "test-key",
            }
        )

    def test_call_creation(self):
        call = self.env["ai.connection.call"].create(
            {
                "connection_id": self.connection.id,
                "prompt": "Hello",
            }
        )
        self.assertEqual(call.state, "draft")
        self.assertTrue(call.prompt)

    def test_call_execution_success(self):
        mock_response = {
            "choices": [{"message": {"content": "Hello back!"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "model": "gpt-4o",
        }
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            call = self.env["ai.connection.call"].create(
                {
                    "connection_id": self.connection.id,
                    "prompt": "Hello",
                }
            )
            call._execute()

        self.assertEqual(call.state, "done")
        self.assertEqual(call.response, "Hello back!")
        self.assertEqual(call.total_tokens, 15)
        self.assertEqual(call.model_used, "gpt-4o")
        self.assertTrue(call.duration > 0)

    def test_call_execution_error(self):
        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("Connection refused")
            call = self.env["ai.connection.call"].create(
                {
                    "connection_id": self.connection.id,
                    "prompt": "Hello",
                }
            )
            call._execute()

        self.assertEqual(call.state, "error")
        self.assertTrue(call.error)

    def test_session_creation(self):
        session = self.env["ai.connection.session"].create(
            {
                "name": "Test Session",
                "connection_id": self.connection.id,
            }
        )
        self.assertEqual(session.name, "Test Session")
        self.assertEqual(session.message_history, [])

    def test_call_with_session(self):
        session = self.env["ai.connection.session"].create(
            {
                "name": "Test Session",
                "connection_id": self.connection.id,
            }
        )
        mock_response = {
            "choices": [{"message": {"content": "Hello!"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "model": "gpt-4o",
        }
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            call = self.env["ai.connection.call"].create(
                {
                    "connection_id": self.connection.id,
                    "session_id": session.id,
                    "prompt": "Say hello",
                }
            )
            call._execute()

        self.assertEqual(call.session_id, session)
        self.assertEqual(len(session.message_history), 2)
        self.assertEqual(session.message_history[1]["content"], "Hello!")

    def test_call_with_tool_loop(self):
        tool_model = self.env["ir.model"].search([("model", "=", "ai.tool")], limit=1)
        tool = self.env["ai.tool"].create(
            {
                "name": "get_date_test",
                "description": "Test tool",
                "model_id": tool_model.id,
                "function_name": "_ai_get_date",
                "kind": "generic",
            }
        )
        self.connection.tool_ids = [(4, tool.id)]

        first_response = {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "get_date_test",
                                    "arguments": "{}",
                                },
                            }
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "model": "gpt-4o",
        }
        second_response = {
            "choices": [{"message": {"content": "Done after tool"}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10},
            "model": "gpt-4o",
        }

        with patch("requests.post") as mock_post:
            mock_first = type(
                "obj",
                (object,),
                {
                    "status_code": 200,
                    "json": lambda s: first_response,
                },
            )()
            mock_second = type(
                "obj",
                (object,),
                {
                    "status_code": 200,
                    "json": lambda s: second_response,
                },
            )()
            mock_post.side_effect = [mock_first, mock_second]
            call = self.env["ai.connection.call"].create(
                {
                    "connection_id": self.connection.id,
                    "prompt": "Use the tool",
                }
            )
            call._execute()

        self.assertEqual(call.state, "done")
        self.assertEqual(call.response, "Done after tool")
        self.assertEqual(call.total_tokens, 45)

    def test_wizard_execution(self):
        mock_response = {
            "choices": [{"message": {"content": "Wizard response"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
            "model": "gpt-4o",
        }
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            wizard = self.env["ai.call.wizard"].create(
                {
                    "connection_id": self.connection.id,
                    "prompt": "Wizard test",
                }
            )
            result = wizard.action_execute()

        call = self.env["ai.connection.call"].browse(result["res_id"])
        self.assertEqual(call.state, "done")
        self.assertEqual(call.response, "Wizard response")

    def test_connection_has_call_and_session_fields(self):
        self.assertTrue(hasattr(self.connection, "call_ids"))
        self.assertTrue(hasattr(self.connection, "session_ids"))
        self.assertTrue(hasattr(self.connection, "tool_ids"))

    def test_action_open_call_wizard(self):
        action = self.connection.action_open_call_wizard()
        self.assertEqual(action["res_model"], "ai.call.wizard")
        self.assertEqual(action["target"], "new")

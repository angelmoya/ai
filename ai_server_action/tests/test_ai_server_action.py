# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase

PATCH_CHAT = "ollama.Client.chat"


def _fake_response(content):
    return {
        "message": {"role": "assistant", "content": content},
        "prompt_eval_count": 5,
        "eval_count": 3,
    }


class TestAiServerAction(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner_model = self.env["ir.model"].search(
            [("model", "=", "res.partner")], limit=1
        )
        self.connection = self.env["ai.connection"].create(
            {
                "name": "Test Connection",
                "kind": "ollama",
                "url": "http://localhost:11434",
                "model": "llama3",
            }
        )

    def _create_action(self, output_mode="none"):
        return self.env["ir.actions.server"].create(
            {
                "name": "Test AI Action",
                "model_id": self.partner_model.id,
                "state": "ai_run",
                "ai_connection_id": self.connection.id,
                "ai_prompt": "Say hello",
                "ai_output_mode": output_mode,
            }
        )

    def test_action_state_added(self):
        states = self.env["ir.actions.server"].fields_get(["state"])
        self.assertTrue(
            any(s[0] == "ai_run" for s in states["state"]["selection"])
        )

    def test_run_action_returns_llm_response(self):
        action = self._create_action()
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        with patch(PATCH_CHAT, return_value=_fake_response("Hello from AI")):
            result = action._run_action_ai_run({"record": partner})
        self.assertEqual(result, "Hello from AI")

    def test_run_action_update_record_field(self):
        action = self._create_action("update_record")
        field = self.env["ir.model.fields"].search(
            [("model_id", "=", self.partner_model.id), ("name", "=", "comment")],
            limit=1,
        )
        action.ai_update_record_field_id = field.id
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        with patch(PATCH_CHAT, return_value=_fake_response("Updated by AI")):
            action._run_action_ai_run({"record": partner})
        self.assertIn("Updated by AI", partner.comment)

    def test_run_action_store_variable(self):
        action = self._create_action("store_variable")
        action.ai_context_variable = "ai_result"
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        context = {"record": partner}
        with patch(PATCH_CHAT, return_value=_fake_response("Stored result")):
            action._run_action_ai_run(context)
        self.assertEqual(context["ai_result"], "Stored result")

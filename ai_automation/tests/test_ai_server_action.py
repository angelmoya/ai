from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestAiServerAction(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["ir.model"].search(
            [("model", "=", "res.partner")], limit=1
        )
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})

    def _create_action(self, output_mode="none"):
        return self.env["ir.actions.server"].create(
            {
                "name": "Test AI Action",
                "model_id": self.partner_model.id,
                "state": "ai_oca",
                "ai_prompt": "Say hello",
                "ai_output_mode": output_mode,
            }
        )

    def _run_action_with_mock(self, action):
        """Execute action with _run patched on the ai.connection model."""
        with patch(
            "odoo.addons.ai_connection.models.ai_connection.AiConnection._run",
            return_value=("This is a mocked response", 10, 5, 1),
        ):
            return action.with_context(
                active_id=self.partner.id, active_model="res.partner"
            ).run()

    def test_action_state_added(self):
        states = self.env["ir.actions.server"].fields_get(["state"])
        self.assertTrue(any(s[0] == "ai_oca" for s in states["state"]["selection"]))

    def test_action_post_message(self):
        action = self._create_action("post_message")
        messages = self.partner.message_ids
        self._run_action_with_mock(action)
        new_msgs = self.partner.message_ids - messages
        self.assertEqual(len(new_msgs), 1)
        self.assertIn("mocked response", new_msgs.body)

    def test_action_update_record(self):
        field = self.env["ir.model.fields"].search(
            [("model_id", "=", self.partner_model.id), ("name", "=", "comment")],
            limit=1,
        )
        action = self._create_action("update_record")
        action.ai_update_record_field_id = field.id
        self._run_action_with_mock(action)
        self.assertIn("mocked response", self.partner.comment)

    def test_action_none(self):
        action = self._create_action("none")
        self._run_action_with_mock(action)

    def test_action_store_variable(self):
        action = self._create_action("store_variable")
        action.ai_context_variable = "ai_result"
        with patch(
            "odoo.addons.ai_connection.models.ai_connection.AiConnection._run",
            return_value=("This is a mocked response", 10, 5, 1),
        ):
            action._run_action_ai_oca({"record": self.partner})

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

    def _create_action(self, output_mode="none", **kwargs):
        vals = {
            "name": "Test AI Action",
            "model_id": self.partner_model.id,
            "state": "ai_oca",
            "ai_prompt": "Say hello",
            "ai_output_mode": output_mode,
        }
        vals.update(kwargs)
        return self.env["ir.actions.server"].create(vals)

    def _run_action_with_mock(self, action, result=None):
        if result is None:
            result = ("This is a mocked response", 10, 5, 1)
        with patch(
            "odoo.addons.ai_connection.models.ai_connection.AiConnection._run",
            return_value=result,
        ):
            return action.with_context(
                active_id=self.partner.id, active_model="res.partner"
            ).run()

    def test_action_state_added(self):
        states = self.env["ir.actions.server"].fields_get(["state"])
        self.assertTrue(any(s[0] == "ai_oca" for s in states["state"]["selection"]))

    def test_compute_mailing_model_real_with_model(self):
        action = self._create_action()
        self.assertEqual(action.mailing_model_real, "res.partner")

    def test_get_ai_prompt_without_record(self):
        action = self._create_action(ai_prompt="<p>Hello world</p>")
        prompt = action._get_ai_prompt(None)
        self.assertIn("Hello world", prompt)

    def test_get_ai_prompt_with_record(self):
        action = self._create_action(ai_prompt="<p>Hello <t t-out='object.name'/></p>")
        prompt = action._get_ai_prompt(self.partner)
        self.assertIn("Test Partner", prompt)

    def test_get_ai_prompt_empty(self):
        action = self._create_action(ai_prompt=False)
        prompt = action._get_ai_prompt(None)
        self.assertEqual(prompt, "")

    def test_action_post_message(self):
        action = self._create_action("post_message")
        messages = self.partner.message_ids
        self._run_action_with_mock(action)
        new_msgs = self.partner.message_ids - messages
        self.assertEqual(len(new_msgs), 1)
        self.assertIn("mocked response", new_msgs.body)

    def test_action_post_message_with_markdown(self):
        action = self._create_action("post_message", ai_prompt="Test")
        messages = self.partner.message_ids
        with patch(
            "odoo.addons.ai_connection.models.ai_connection.AiConnection._run",
            return_value=("**bold text**", 10, 5, 1),
        ):
            action.with_context(
                active_id=self.partner.id, active_model="res.partner"
            ).run()
        new_msgs = self.partner.message_ids - messages
        self.assertEqual(len(new_msgs), 1)
        self.assertIn("bold text", new_msgs.body)

    def test_action_post_message_dead_record(self):
        action = self._create_action("post_message")
        action._post_run_action_ai_run("result", {}, self.partner)
        self.partner.unlink()
        action._post_run_action_ai_run("result", {}, self.partner)

    def test_action_update_record_text(self):
        field = self.env["ir.model.fields"].search(
            [("model_id", "=", self.partner_model.id), ("name", "=", "comment")],
            limit=1,
        )
        action = self._create_action("update_record")
        action.ai_update_record_field_id = field.id
        self._run_action_with_mock(action)
        self.assertIn("mocked response", self.partner.comment)

    def test_action_update_record_html_field_with_markdown(self):
        field = self.env["ir.model.fields"].search(
            [
                ("model_id", "=", self.partner_model.id),
                ("ttype", "=", "html"),
            ],
            limit=1,
        )
        self.assertTrue(field, "No html field found on res.partner")
        action = self._create_action("update_record")
        action.ai_update_record_field_id = field.id
        with patch(
            "odoo.addons.ai_connection.models.ai_connection.AiConnection._run",
            return_value=("**bold**", 10, 5, 1),
        ):
            action.with_context(
                active_id=self.partner.id, active_model="res.partner"
            ).run()
        self.assertIn("bold", getattr(self.partner, field.name, ""))

    def test_action_update_record_html_field_without_markdown(self):
        field = self.env["ir.model.fields"].search(
            [
                ("model_id", "=", self.partner_model.id),
                ("ttype", "=", "html"),
            ],
            limit=1,
        )
        self.assertTrue(field, "No html field found on res.partner")
        action = self._create_action("update_record")
        action.ai_update_record_field_id = field.id
        with (
            patch(
                "odoo.addons.ai_connection.models.ai_connection.AiConnection._run",
                return_value=("plain result", 10, 5, 1),
            ),
            patch(
                "odoo.addons.ai_server_action.models.ir_actions_server.markdown",
                None,
            ),
        ):
            action.with_context(
                active_id=self.partner.id, active_model="res.partner"
            ).run()
        self.assertIn("plain result", getattr(self.partner, field.name, ""))

    def test_action_update_record_without_field_noop(self):
        action = self._create_action("update_record")
        action.ai_update_record_field_id = False
        self._run_action_with_mock(action)

    def test_action_update_record_without_record(self):
        action = self._create_action("update_record")
        field = self.env["ir.model.fields"].search(
            [("model_id", "=", self.partner_model.id), ("name", "=", "comment")],
            limit=1,
        )
        action.ai_update_record_field_id = field.id
        action._post_run_action_ai_run("result", {}, None)

    def test_action_none(self):
        action = self._create_action("none")
        self._run_action_with_mock(action)

    def test_action_store_variable(self):
        action = self._create_action("store_variable")
        action.ai_context_variable = "ai_result"
        eval_context = {"record": self.partner}
        with patch(
            "odoo.addons.ai_connection.models.ai_connection.AiConnection._run",
            return_value=("Variable value", 10, 5, 1),
        ):
            action._run_action_ai_oca(eval_context)
        self.assertEqual(eval_context["ai_result"], "Variable value")

    def test_action_store_variable_empty_name(self):
        action = self._create_action("store_variable")
        action.ai_context_variable = False
        eval_context = {"record": self.partner}
        with patch(
            "odoo.addons.ai_connection.models.ai_connection.AiConnection._run",
            return_value=("Value", 10, 5, 1),
        ):
            action._run_action_ai_oca(eval_context)
        self.assertNotIn("ai_result", eval_context)

    def test_prepare_message_body_with_markdown(self):
        action = self._create_action()
        with patch(
            "odoo.addons.ai_server_action.models.ir_actions_server.markdown"
        ) as mock_md:
            mock_md.markdown.return_value = "<p>rendered</p>"
            result = action._prepare_message_body("**bold**")
            mock_md.markdown.assert_called_once_with("**bold**")
            self.assertIn("rendered", result)

    def test_prepare_message_body_without_markdown(self):
        action = self._create_action()
        with patch(
            "odoo.addons.ai_server_action.models.ir_actions_server.markdown",
            None,
        ):
            result = action._prepare_message_body("plain text")
            self.assertIn("plain text", result)

    def test_action_with_tools(self):
        action = self._create_action("none")
        tool = self.env.ref("ai_tool.current_date", raise_if_not_found=False)
        if tool:
            action.ai_tool_ids = [(4, tool.id)]
        self._run_action_with_mock(action)

    def test_run_action_ai_oca_returns_first_element(self):
        action = self._create_action("none")
        with patch(
            "odoo.addons.ai_connection.models.ai_connection.AiConnection._run",
            return_value=("first", "second", "third"),
        ):
            action._run_action_ai_oca({"record": self.partner})

    def test_run_action_ai_oca_no_eval_context(self):
        action = self._create_action("none")
        with patch(
            "odoo.addons.ai_connection.models.ai_connection.AiConnection._run",
            return_value=("ok", 1, 1, 1),
        ):
            action._run_action_ai_oca()

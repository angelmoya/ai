# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests import common, new_test_user

PATCH_RUN = "odoo.addons.ai_agent.models.ai_agent.AiAgent.run"
VIEW_CONTEXT = {
    "model": "res.partner",
    "view_type": "form",
    "domain": [],
    "active_id": 1,
    "active_ids": [1],
    "view_id": 123,
}
CHANNEL_VIEW_CONTEXT = {
    "model": "discuss.channel",
    "view_type": "form",
    "domain": [],
    "active_id": 1,
    "active_ids": [1],
}


class TestAiAgentChatterWebContext(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, mail_create_nosubscribe=True)
        )
        cls.connection = cls.env["ai.connection"].create(
            {
                "name": "Test Connection",
                "kind": "ollama",
                "url": "http://localhost:11434",
                "model": "llama3",
            }
        )
        cls.agent = cls.env["ai.agent"].create(
            {
                "name": "Test Agent",
                "goal": "Help the user.",
                "connection_id": cls.connection.id,
            }
        )
        cls.ai_user = new_test_user(
            cls.env,
            login="test-ai-vc",
            groups="base.group_user",
        )
        cls.ai_user.write({"agent_id": cls.agent.id})
        cls.user = new_test_user(
            cls.env,
            login="test-human-vc",
            groups="base.group_user",
        )

    def test_get_view_context_prompt_formatted(self):
        record = self.env["res.partner"].create({"name": "Test"})
        prompt = record.with_context(
            ai_view_context=VIEW_CONTEXT
        )._get_view_context_prompt()
        self.assertIn("## View Context", prompt)
        self.assertIn("res.partner", prompt)
        self.assertIn("form", prompt)
        self.assertIn("123", prompt)

    def test_get_view_context_prompt_empty_when_no_context(self):
        record = self.env["res.partner"].create({"name": "Test"})
        prompt = record._get_view_context_prompt()
        self.assertEqual(prompt, "")

    def test_get_view_context_prompt_empty_for_channel_model(self):
        record = self.env["res.partner"].create({"name": "Test"})
        prompt = record.with_context(
            ai_view_context=CHANNEL_VIEW_CONTEXT
        )._get_view_context_prompt()
        self.assertEqual(prompt, "")

    def test_build_thread_prompt_includes_view_context(self):
        record = self.env["res.partner"].create({"name": "Test Partner"})
        partner = self.user.partner_id
        with patch(PATCH_RUN) as mock_run:
            mock_run.side_effect = self._make_call_mock()
            record.with_user(self.user).with_context(
                ai_view_context=VIEW_CONTEXT
            ).message_post(
                body="Hello",
                partner_ids=[self.ai_user.partner_id.id],
            )
            call_kwargs = mock_run.call_args[1]
            prompt = call_kwargs.get("prompt", "")
            self.assertIn("## View Context", prompt)
            self.assertIn("res.partner", prompt)
            self.assertIn("form", prompt)

    @staticmethod
    def _make_call_mock(response_text="Hello! I'm the AI agent."):
        def _run_side_effect(self, prompt, thread=None, user=None, record=None):
            thread.message_history = [
                {"role": "assistant", "content": response_text}
            ]
            self.env["ai.connection.call"].create(
                {
                    "connection_id": self.connection_id.id,
                    "prompt": prompt,
                    "response": response_text,
                    "state": "done",
                }
            )

        return _run_side_effect

    def test_build_thread_prompt_no_view_context(self):
        record = self.env["res.partner"].create({"name": "Test Partner"})
        with patch(PATCH_RUN) as mock_run:
            mock_run.side_effect = self._make_call_mock()
            record.with_user(self.user).message_post(
                body="Hello",
                partner_ids=[self.ai_user.partner_id.id],
            )
            call_kwargs = mock_run.call_args[1]
            prompt = call_kwargs.get("prompt", "")
            self.assertNotIn("## View Context", prompt)

    def test_build_channel_prompt_includes_view_context(self):
        chat = self.env["discuss.channel"].with_user(self.user.id).create(
            {
                "name": "Test Chat",
                "channel_type": "chat",
                "channel_member_ids": [
                    (0, 0, {"partner_id": self.ai_user.partner_id.id}),
                    (0, 0, {"partner_id": self.user.partner_id.id}),
                ],
            }
        )
        with patch(PATCH_RUN) as mock_run:
            mock_run.side_effect = self._make_call_mock()
            chat.with_user(self.user).with_context(
                ai_view_context={
                    "model": "sale.order",
                    "view_type": "list",
                    "domain": [["state", "=", "sale"]],
                }
            ).message_post(body="Check orders")
            call_kwargs = mock_run.call_args[1]
            prompt = call_kwargs.get("prompt", "")
            self.assertIn("## View Context", prompt)
            self.assertIn("sale.order", prompt)
            self.assertIn("list", prompt)
            self.assertIn("state", prompt)

    def test_build_channel_prompt_no_view_context(self):
        chat = self.env["discuss.channel"].with_user(self.user.id).create(
            {
                "name": "Test Chat 2",
                "channel_type": "chat",
                "channel_member_ids": [
                    (0, 0, {"partner_id": self.ai_user.partner_id.id}),
                    (0, 0, {"partner_id": self.user.partner_id.id}),
                ],
            }
        )
        with patch(PATCH_RUN) as mock_run:
            mock_run.side_effect = self._make_call_mock()
            chat.with_user(self.user).message_post(body="No context")
            call_kwargs = mock_run.call_args[1]
            prompt = call_kwargs.get("prompt", "")
            self.assertNotIn("## View Context", prompt)

    def test_view_context_between_document_and_history(self):
        partner = self.env["res.partner"].create(
            {"name": "ACME Corp"}
        )
        channel = self.env["discuss.channel"].with_user(self.user.id).create(
            {
                "name": "Partner Chat",
                "channel_type": "chat",
                "channel_member_ids": [
                    (0, 0, {"partner_id": self.ai_user.partner_id.id}),
                    (0, 0, {"partner_id": self.user.partner_id.id}),
                ],
            }
        )
        with patch(PATCH_RUN) as mock_run:
            mock_run.side_effect = self._make_call_mock()
            channel.with_user(self.user).with_context(
                ai_view_context={
                    "model": "res.partner",
                    "view_type": "form",
                    "active_id": partner.id,
                }
            ).message_post(
                body="Tell me about this partner",
                model="res.partner",
                res_id=partner.id,
            )
            call_kwargs = mock_run.call_args[1]
            prompt = call_kwargs.get("prompt", "")
            doc_idx = prompt.index("## Current Document")
            vc_idx = prompt.index("## View Context")
            hist_idx = prompt.index("## Conversation History")
            self.assertLess(doc_idx, vc_idx)
            self.assertLess(vc_idx, hist_idx)

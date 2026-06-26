# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests import common, new_test_user

PATCH_RUN = "odoo.addons.ai_agent.models.ai_agent.AiAgent.run"


class TestAiAgentChatter(common.TransactionCase):
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
            login="test-ai-chatter",
            groups="base.group_user",
        )
        cls.ai_user.write({"agent_id": cls.agent.id})
        cls.user = new_test_user(
            cls.env,
            login="test-human-chatter",
            groups="base.group_user",
        )
        cls.chat = (
            cls.env["discuss.channel"]
            .with_user(cls.user.id)
            .create(
                {
                    "name": "Test Chat",
                    "channel_type": "chat",
                    "channel_member_ids": [
                        (0, 0, {"partner_id": cls.ai_user.partner_id.id}),
                        (0, 0, {"partner_id": cls.user.partner_id.id}),
                    ],
                }
            )
        )
        cls.channel = cls.env["discuss.channel"].create(
            {
                "name": "Main Channel",
                "channel_type": "channel",
                "channel_member_ids": [
                    (0, 0, {"partner_id": cls.ai_user.partner_id.id}),
                    (0, 0, {"partner_id": cls.user.partner_id.id}),
                    (0, 0, {"partner_id": cls.env.user.partner_id.id}),
                ],
            }
        )

    @staticmethod
    def _make_call_mock(response_text="Hello! I'm the AI agent."):
        def _run_side_effect(self, prompt, thread=None, user=None, record=None):
            thread.message_history = [
                {"role": "assistant", "content": response_text}
            ]
            call = self.env["ai.connection.call"].create(
                {
                    "connection_id": self.connection_id.id,
                    "prompt": prompt,
                    "response": response_text,
                    "state": "done",
                }
            )

        return _run_side_effect

    def test_user_status(self):
        self.assertEqual("online", self.ai_user.partner_id.im_status)
        self.assertEqual("online", self.ai_user.im_status)

    def test_chat_triggers_agent(self):
        self.assertFalse(
            self.env["mail.message"].search(
                [("res_id", "=", self.chat.id), ("model", "=", "discuss.channel")]
            )
        )
        with patch(PATCH_RUN) as mock_run:
            mock_run.side_effect = self._make_call_mock()
            self.chat.with_user(self.user.id).message_post(body="Hello AI!")
            mock_run.assert_called_once()
        self.assertEqual(
            2,
            self.env["mail.message"].search_count(
                [("res_id", "=", self.chat.id), ("model", "=", "discuss.channel")]
            ),
        )

    def test_channel_mention_triggers_agent(self):
        self.assertFalse(
            self.env["mail.message"].search(
                [("res_id", "=", self.channel.id),
                 ("model", "=", "discuss.channel")]
            )
        )
        with patch(PATCH_RUN) as mock_run:
            mock_run.side_effect = self._make_call_mock()
            self.channel.with_user(self.user.id).message_post(
                body="Hello AI!",
                partner_ids=[self.ai_user.partner_id.id],
            )
            mock_run.assert_called_once()
        self.assertEqual(
            2,
            self.env["mail.message"].search_count(
                [("res_id", "=", self.channel.id),
                 ("model", "=", "discuss.channel")]
            ),
        )

    def test_channel_no_mention_does_not_trigger(self):
        self.assertFalse(
            self.env["mail.message"].search(
                [("res_id", "=", self.channel.id),
                 ("model", "=", "discuss.channel")]
            )
        )
        with patch(PATCH_RUN) as mock_run:
            self.channel.with_user(self.user.id).message_post(
                body="Hello everyone!"
            )
            mock_run.assert_not_called()
        self.assertEqual(
            1,
            self.env["mail.message"].search_count(
                [("res_id", "=", self.channel.id),
                 ("model", "=", "discuss.channel")]
            ),
        )

    def test_ai_does_not_trigger_another_ai(self):
        self.ai_user2 = new_test_user(
            self.env,
            login="test-ai-chatter-2",
            groups="base.group_user",
        )
        self.ai_user2.write({"agent_id": self.agent.id})
        self.chat.message_post(
            body="I am another AI",
            author_id=self.ai_user.partner_id.id,
        )
        with patch(PATCH_RUN) as mock_run:
            self.chat.with_user(self.user.id).message_post(
                body="Hello from human"
            )
            self.assertEqual(1, mock_run.call_count)

    def test_channel_thread_created(self):
        with patch(PATCH_RUN) as mock_run:
            mock_run.side_effect = self._make_call_mock()
            self.chat.with_user(self.user.id).message_post(body="Hello AI!")
        thread = self.env["ai.agent.thread"].search(
            [("agent_id", "=", self.agent.id),
             ("channel_id", "=", self.chat.id)]
        )
        self.assertTrue(thread.exists())
        self.assertEqual(thread.channel_id, self.chat)

    def test_channel_thread_reused(self):
        with patch(PATCH_RUN) as mock_run:
            mock_run.side_effect = self._make_call_mock()
            self.chat.with_user(self.user.id).message_post(body="First message")
            self.chat.with_user(self.user.id).message_post(body="Second message")
        threads = self.env["ai.agent.thread"].search(
            [("agent_id", "=", self.agent.id),
             ("channel_id", "=", self.chat.id)]
        )
        self.assertEqual(len(threads), 1)

    def test_get_ai_context_form_view(self):
        partner = self.env.ref("base.res_partner_1")
        ctx = partner._get_ai_context()
        self.assertIn("name", ctx)
        self.assertNotIn("id", ctx)

    def test_get_ai_context_one2many(self):
        partner = self.env["res.partner"].create(
            {"name": "Test Partner", "email": "test@example.com"}
        )
        self.env["res.partner.bank"].create(
            {
                "partner_id": partner.id,
                "acc_number": "ES1234567890",
            }
        )
        ctx = partner._get_ai_context()
        self.assertIn("name", ctx)
        self.assertIn("bank_ids", ctx)

    def test_document_context_injection(self):
        partner = self.env["res.partner"].create(
            {"name": "ACME Corp"}
        )
        channel = (
            self.env["discuss.channel"]
            .with_user(self.user.id)
            .create(
                {
                    "name": "Partner Chat",
                    "channel_type": "chat",
                    "channel_member_ids": [
                        (0, 0, {"partner_id": self.ai_user.partner_id.id}),
                        (0, 0, {"partner_id": self.user.partner_id.id}),
                    ],
                }
            )
        )
        with patch(PATCH_RUN) as mock_run:
            mock_run.side_effect = self._make_call_mock()
            channel.with_user(self.user.id).message_post(
                body="Tell me about this partner",
                model="res.partner",
                res_id=partner.id,
            )
            call_kwargs = mock_run.call_args[1]
            prompt = call_kwargs.get("prompt", "")
            self.assertIn("ACME Corp", prompt)

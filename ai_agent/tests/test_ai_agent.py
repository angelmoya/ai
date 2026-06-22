# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase

PATCH_SEND = (
    "odoo.addons.ai_connection_base_openai.client.AiConnectionOpenAIClient._send_request"
)

RESPONSE_HELLO = {
    "choices": [{"message": {"role": "assistant", "content": "Hello!"}}],
    "usage": {},
}
RESPONSE_PLAN = {
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": '[{"description": "step 1"}]',
            }
        }
    ],
    "usage": {},
}
RESPONSE_DONE = {
    "choices": [{"message": {"role": "assistant", "content": "Done"}}],
    "usage": {},
}




class TestAiAgent(TransactionCase):
    def setUp(self):
        super().setUp()
        self.connection = self.env["ai.connection"].create(
            {
                "name": "Test Connection",
                "kind": "base_openai",
                "url": "https://api.example.com/v1",
                "model": "gpt-4o",
                "api_key": "test-key",
            }
        )
        self.agent = self.env["ai.agent"].create(
            {
                "name": "Test Agent",
                "goal": "Help the user.",
                "connection_id": self.connection.id,
            }
        )

    def test_agent_creation(self):
        self.assertTrue(self.agent.exists())
        self.assertEqual(self.agent.connection_id, self.connection)
        self.assertFalse(self.agent.planning_enabled)

    def test_get_or_create_thread(self):
        user = self.env.user
        thread = self.agent._get_or_create_thread(user)
        self.assertTrue(thread.exists())
        self.assertEqual(thread.agent_id, self.agent)
        self.assertEqual(thread.user_id, user)
        # Second call returns same thread
        thread2 = self.agent._get_or_create_thread(user)
        self.assertEqual(thread, thread2)

    def test_build_system_prompt(self):
        prompt = self.agent._build_system_prompt()
        self.assertIn("Help the user.", prompt)

    def test_run_prompt(self):
        user = self.env.user
        with patch(PATCH_SEND, return_value=RESPONSE_HELLO):
            call = self.agent.run("Say hi", user=user)
        self.assertEqual(call._name, "ai.connection.call")
        self.assertEqual(call.response, "Hello!")
        self.assertEqual(call.state, "done")

    def test_plan_and_run(self):
        self.agent.planning_enabled = True
        self.agent.plan_requires_approval = False
        user = self.env.user
        with patch(PATCH_SEND, side_effect=[RESPONSE_PLAN, RESPONSE_DONE]):
            plan = self.agent.run("Do something", user=user)
        self.assertEqual(plan._name, "ai.agent.plan")
        self.assertEqual(plan.state, "done")
        self.assertTrue(plan.step_ids)

    def test_job_run(self):
        job = self.env["ai.agent.job"].create(
            {
                "name": "Test Job",
                "agent_id": self.agent.id,
                "user_id": self.env.user.id,
                "prompt": "Say hi",
            }
        )
        with patch(PATCH_SEND, return_value=RESPONSE_HELLO):
            job.action_run()
        self.assertEqual(job.state, "done")
        self.assertEqual(job.last_result, "Hello!")

# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.tests.common import TransactionCase

PATCH_SEND = (
    "odoo.addons.ai_connection_base_openai.client.AiConnectionOpenAIClient._send_request"
)

RESPONSE_ORCH_PLAN = {
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": '[{"role": "worker", "description": "do work"}]',
            }
        }
    ],
    "usage": {},
}
RESPONSE_DONE = {
    "choices": [{"message": {"role": "assistant", "content": "Done"}}],
    "usage": {},
}




class TestAiAgentOrchestrator(TransactionCase):
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
        self.member_agent = self.env["ai.agent"].create(
            {
                "name": "Member Agent",
                "goal": "Execute tasks.",
                "connection_id": self.connection.id,
            }
        )
        self.orchestrator = self.env["ai.agent"].create(
            {
                "name": "Orchestrator",
                "goal": "Coordinate tasks.",
                "connection_id": self.connection.id,
                "is_orchestrator": True,
            }
        )
        self.env["ai.agent.orchestrator.member"].create(
            {
                "orchestrator_id": self.orchestrator.id,
                "agent_id": self.member_agent.id,
                "role": "worker",
            }
        )

    def test_orchestrator_flag(self):
        self.assertTrue(self.orchestrator.is_orchestrator)
        self.assertFalse(self.member_agent.is_orchestrator)

    def test_member_assignment(self):
        self.assertEqual(len(self.orchestrator.orchestrator_member_ids), 1)
        self.assertEqual(
            self.orchestrator.orchestrator_member_ids.agent_id, self.member_agent
        )

    def test_orchestrator_run(self):
        user = self.env.user
        with patch(PATCH_SEND, side_effect=[RESPONSE_ORCH_PLAN, RESPONSE_DONE]):
            plan = self.orchestrator.run("Do work", user=user)
        self.assertEqual(plan._name, "ai.agent.plan")
        self.assertEqual(plan.state, "done")
        self.assertTrue(plan.step_ids)

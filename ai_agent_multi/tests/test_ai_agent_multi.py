# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestAiAgentMulti(TransactionCase):
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
                "name": "Restricted Agent",
                "goal": "Help.",
                "connection_id": self.connection.id,
            }
        )
        self.user = self.env["res.users"].create(
            {
                "name": "Test User",
                "login": "test_user",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )

    def test_no_rules_allows_all(self):
        # Without access rules, the agent is visible to everyone
        agents = self.env["ai.agent"].with_user(self.user).search(
            [("id", "=", self.agent.id)]
        )
        self.assertIn(self.agent, agents)

    def test_access_rule_restricts_user(self):
        self.env["ai.agent.access.rule"].create(
            {
                "agent_id": self.agent.id,
                "user_id": self.env.user.id,
            }
        )
        agents = self.env["ai.agent"].with_user(self.user).search(
            [("id", "=", self.agent.id)]
        )
        self.assertNotIn(self.agent, agents)

    def test_access_rule_allows_user(self):
        self.env["ai.agent.access.rule"].create(
            {
                "agent_id": self.agent.id,
                "user_id": self.user.id,
            }
        )
        agents = self.env["ai.agent"].with_user(self.user).search(
            [("id", "=", self.agent.id)]
        )
        self.assertIn(self.agent, agents)

    def test_group_access_rule(self):
        group = self.env.ref("base.group_user")
        self.env["ai.agent.access.rule"].create(
            {
                "agent_id": self.agent.id,
                "group_id": group.id,
            }
        )
        agents = self.env["ai.agent"].with_user(self.user).search(
            [("id", "=", self.agent.id)]
        )
        self.assertIn(self.agent, agents)

    def test_run_checks_access(self):
        self.env["ai.agent.access.rule"].create(
            {
                "agent_id": self.agent.id,
                "user_id": self.env.user.id,
            }
        )
        with self.assertRaises(AccessError):
            self.agent.with_user(self.user).run("test")

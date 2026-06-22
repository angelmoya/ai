# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestAiToolServerAction(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner_model = self.env["ir.model"].search(
            [("model", "=", "res.partner")], limit=1
        )
        self.server_action = self.env["ir.actions.server"].create(
            {
                "name": "Mark as Test",
                "model_id": self.partner_model.id,
                "state": "code",
                "code": "record.write({'comment': 'test'})",
            }
        )

    def test_tool_fields_added(self):
        tool = self.env["ai.tool"].create(
            {
                "name": "Test Tool",
                "model_id": self.env["ir.model"]._get("ai.tool.server.action.runner").id,
                "function_name": "_ai_server_action_wrapper",
                "kind": "generic",
                "is_server_action": True,
                "server_action_id": self.server_action.id,
            }
        )
        self.assertTrue(tool.is_server_action)
        self.assertEqual(tool.server_action_id, self.server_action)

    def test_tool_executes_server_action(self):
        tool = self.env["ai.tool"].create(
            {
                "name": "Test Tool",
                "model_id": self.env["ir.model"]._get("ai.tool.server.action.runner").id,
                "function_name": "_ai_server_action_wrapper",
                "kind": "generic",
                "is_server_action": True,
                "server_action_id": self.server_action.id,
            }
        )
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        result = tool._execute_tool(record=partner)
        self.assertIn("test", partner.comment)
        self.assertEqual(result, {})

    def test_wizard_creates_tool(self):
        wizard = self.env["ai.tool.server.action.wizard"].create(
            {
                "server_action_id": self.server_action.id,
                "name": "Wizard Tool",
                "description": "Created from wizard",
            }
        )
        res = wizard.action_create_tool()
        tool = self.env["ai.tool"].browse(res["res_id"])
        self.assertTrue(tool.exists())
        self.assertTrue(tool.is_server_action)
        self.assertEqual(tool.server_action_id, self.server_action)

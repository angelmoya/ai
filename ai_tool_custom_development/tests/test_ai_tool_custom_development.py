from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestAiToolCustomDevelopment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner"})

    def _get_tool(self, xml_id):
        return self.env.ref(xml_id)

    # ------------------------------------------------------------------
    # TEST: create_model
    # ------------------------------------------------------------------

    def test_create_model(self):
        tool = self._get_tool("ai_tool_custom_development.create_model")
        result = tool._execute_tool(
            prefix="test_custom",
            model_name="project",
            description="Test Projects",
            fields=[
                {"name": "name", "field_type": "char", "string": "Project Name"},
                {"name": "active", "field_type": "boolean", "string": "Active"},
                {"name": "deadline", "field_type": "date", "string": "Deadline"},
            ],
        )
        self.assertEqual(result["model"], "x_test_custom.project")
        self.assertTrue(result["model_id"])
        self.assertIn("x_test_custom_name", result["fields_created"])
        self.assertIn("x_test_custom_active", result["fields_created"])
        self.assertIn("x_test_custom_deadline", result["fields_created"])

        ir_model = self.env["ir.model"].search(
            [("model", "=", "x_test_custom.project")], limit=1
        )
        self.assertTrue(ir_model)
        fields_count = self.env["ir.model.fields"].search_count(
            [("model_id", "=", ir_model.id)]
        )
        self.assertGreaterEqual(fields_count, 3)

    def test_create_model_duplicate(self):
        tool = self._get_tool("ai_tool_custom_development.create_model")
        tool._execute_tool(
            prefix="test_custom",
            model_name="duplicate_test",
            fields=[{"name": "name", "field_type": "char"}],
        )
        with self.assertRaises(UserError):
            tool._execute_tool(
                prefix="test_custom",
                model_name="duplicate_test",
                fields=[{"name": "name", "field_type": "char"}],
            )

    def test_create_model_invalid_prefix(self):
        tool = self._get_tool("ai_tool_custom_development.create_model")
        with self.assertRaises(UserError):
            tool._execute_tool(
                prefix="invalid prefix!",
                model_name="test",
                fields=[{"name": "name", "field_type": "char"}],
            )

    # ------------------------------------------------------------------
    # TEST: create_field
    # ------------------------------------------------------------------

    def test_create_field_on_standard_model(self):
        tool = self._get_tool("ai_tool_custom_development.create_field")
        result = tool._execute_tool(
            prefix="test_custom",
            model="res.partner",
            name="assistant_phone",
            field_type="char",
            string="Assistant Phone",
        )
        self.assertEqual(result["field_name"], "x_test_custom_assistant_phone")
        self.assertTrue(result["field_id"])

        field = self.env["ir.model.fields"].browse(result["field_id"])
        self.assertTrue(field.exists())
        self.assertEqual(field.ttype, "char")

    def test_create_field_duplicate(self):
        tool = self._get_tool("ai_tool_custom_development.create_field")
        tool._execute_tool(
            prefix="test_custom",
            model="res.partner",
            name="dup_field",
            field_type="char",
        )
        with self.assertRaises(UserError):
            tool._execute_tool(
                prefix="test_custom",
                model="res.partner",
                name="dup_field",
                field_type="char",
            )

    def test_create_field_relation(self):
        tool = self._get_tool("ai_tool_custom_development.create_field")
        result = tool._execute_tool(
            prefix="test_custom",
            model="res.partner",
            name="ref_user",
            field_type="many2one",
            relation="res.users",
            string="Reference User",
        )
        field = self.env["ir.model.fields"].browse(result["field_id"])
        self.assertEqual(field.relation, "res.users")
        self.assertEqual(field.ttype, "many2one")

    # ------------------------------------------------------------------
    # TEST: create_view
    # ------------------------------------------------------------------

    def test_create_view_form(self):
        tool = self._get_tool("ai_tool_custom_development.create_model")
        tool._execute_tool(
            prefix="test_custom",
            model_name="view_test",
            fields=[{"name": "name", "field_type": "char"}],
        )

        view_tool = self._get_tool("ai_tool_custom_development.create_view")
        result = view_tool._execute_tool(
            prefix="test_custom",
            name="view_test.form",
            model="x_test_custom.view_test",
            view_type="form",
            arch="<form><sheet><group><field name='x_test_custom_name'/></group></sheet></form>",
        )
        self.assertTrue(result["view_id"])
        view = self.env["ir.ui.view"].browse(result["view_id"])
        self.assertTrue(view.exists())
        self.assertEqual(view.type, "form")
        self.assertIn("x_test_custom_name", view.arch_db)

    def test_create_view_auto_generate(self):
        view_tool = self._get_tool("ai_tool_custom_development.create_view")
        result = view_tool._execute_tool(
            prefix="test_custom",
            name="auto_list",
            model="res.partner",
            view_type="list",
            field_list=["name", "email"],
        )
        view = self.env["ir.ui.view"].browse(result["view_id"])
        self.assertIn('field name="name"', view.arch_db)
        self.assertIn('field name="email"', view.arch_db)

    # ------------------------------------------------------------------
    # TEST: create_server_action
    # ------------------------------------------------------------------

    def test_create_server_action(self):
        tool = self._get_tool("ai_tool_custom_development.create_server_action")
        result = tool._execute_tool(
            prefix="test_custom",
            name="log_partner",
            model_id="res.partner",
            action_type="code",
            code="log('test')",
        )
        self.assertTrue(result["action_id"])
        action = self.env["ir.actions.server"].browse(result["action_id"])
        self.assertTrue(action.exists())
        self.assertTrue(action.name.startswith("test_custom"))

    # ------------------------------------------------------------------
    # TEST: create_scheduled_action
    # ------------------------------------------------------------------

    def test_create_scheduled_action(self):
        tool = self._get_tool("ai_tool_custom_development.create_scheduled_action")
        result = tool._execute_tool(
            prefix="test_custom",
            name="daily_cleanup",
            model_id="res.partner",
            code="model.search([]).do_something()",
            interval_number=1,
            interval_type="days",
        )
        self.assertTrue(result["cron_id"])
        cron = self.env["ir.cron"].browse(result["cron_id"])
        self.assertTrue(cron.exists())
        self.assertEqual(cron.interval_number, 1)
        self.assertEqual(cron.interval_type, "days")

    # ------------------------------------------------------------------
    # TEST: create_access_rights
    # ------------------------------------------------------------------

    def test_create_access_rights_default(self):
        tool = self._get_tool("ai_tool_custom_development.create_model")
        tool._execute_tool(
            prefix="test_custom",
            model_name="access_test",
            fields=[{"name": "name", "field_type": "char"}],
        )

        acl_tool = self._get_tool("ai_tool_custom_development.create_access_rights")
        result = acl_tool._execute_tool(
            model="x_test_custom.access_test",
            default_access="base.group_user:read,write",
        )
        self.assertEqual(result["model"], "x_test_custom.access_test")
        self.assertEqual(result["rules_created"], 1)

        ir_model = self.env["ir.model"].search(
            [("model", "=", "x_test_custom.access_test")], limit=1
        )
        acls = self.env["ir.model.access"].search([
            ("model_id", "=", ir_model.id),
        ])
        self.assertEqual(len(acls), 1)
        self.assertTrue(acls.perm_read)
        self.assertTrue(acls.perm_write)
        self.assertFalse(acls.perm_unlink)

    def test_create_access_rights_rules(self):
        acl_tool = self._get_tool("ai_tool_custom_development.create_access_rights")
        result = acl_tool._execute_tool(
            model="res.partner",
            rules=[{
                "group_xml_id": "base.group_user",
                "perm_read": True,
                "perm_write": True,
                "perm_create": False,
                "perm_unlink": False,
            }],
        )
        self.assertEqual(result["rules_created"], 1)

    # ------------------------------------------------------------------
    # TEST: add_field_to_view
    # ------------------------------------------------------------------

    def test_add_field_to_view_after(self):
        create_tool = self._get_tool("ai_tool_custom_development.create_field")
        field_result = create_tool._execute_tool(
            prefix="test_custom",
            model="res.partner",
            name="extra_note",
            field_type="text",
        )
        field_name = field_result["field_name"]

        view_tool = self._get_tool("ai_tool_custom_development.add_field_to_view")
        partner_form = self.env["ir.ui.view"].search([
            ("model", "=", "res.partner"),
            ("type", "=", "form"),
        ], limit=1)

        result = view_tool._execute_tool(
            view_id=str(partner_form.id),
            fields=[{
                "field_name": field_name,
                "position": "after",
                "target": "name",
            }],
        )
        self.assertIn(field_name, result["fields_added"])
        self.assertIn(field_name, partner_form.read(["arch_db"])[0]["arch_db"])

    def test_add_field_new_page(self):
        create_tool = self._get_tool("ai_tool_custom_development.create_field")
        create_tool._execute_tool(
            prefix="test_custom",
            model="res.partner",
            name="page_field",
            field_type="char",
        )

        view_tool = self._get_tool("ai_tool_custom_development.add_field_to_view")
        partner_form = self.env["ir.ui.view"].search([
            ("model", "=", "res.partner"),
            ("type", "=", "form"),
        ], limit=1)

        result = view_tool._execute_tool(
            view_id=str(partner_form.id),
            fields=[{
                "field_name": "x_test_custom_page_field",
                "position": "inside_new_page",
                "target": "AI Custom Fields",
            }],
        )
        self.assertIn("x_test_custom_page_field", result["fields_added"])
        arch = partner_form.read(["arch_db"])[0]["arch_db"]
        self.assertIn("AI Custom Fields", arch)

    # ------------------------------------------------------------------
    # TEST: get_model_views
    # ------------------------------------------------------------------

    def test_get_model_views_all(self):
        tool = self._get_tool("ai_tool_custom_development.get_model_views")
        result = tool._execute_tool(model="res.partner")
        self.assertIn("views", result)
        self.assertTrue(len(result["views"]) > 0)
        self.assertTrue(any(v["type"] == "form" for v in result["views"]))
        self.assertTrue(any(v["type"] == "list" for v in result["views"]))
        for v in result["views"]:
            self.assertIn("id", v)
            self.assertIn("name", v)
            self.assertIn("type", v)
            self.assertIn("arch", v)
            self.assertIn("inherit", v)

    def test_get_model_views_filter_type(self):
        tool = self._get_tool("ai_tool_custom_development.get_model_views")
        result = tool._execute_tool(model="res.partner", view_type="search")
        self.assertIn("views", result)
        for v in result["views"]:
            self.assertEqual(v["type"], "search")

    def test_get_model_views_no_model(self):
        tool = self._get_tool("ai_tool_custom_development.get_model_views")
        result = tool._execute_tool(model="nonexistent.model")
        self.assertIn("views", result)
        self.assertEqual(len(result["views"]), 0)

    # ------------------------------------------------------------------
    # TEST: export_customizations
    # ------------------------------------------------------------------

    def test_export_customizations(self):
        export_tool = self._get_tool("ai_tool_custom_development.export_customizations")
        result = export_tool._execute_tool(prefix="test_custom")
        self.assertIn("download_url", result)
        self.assertEqual(result["module_name"], "test_custom")

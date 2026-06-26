# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import common


class TestViewContext(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.ctx_model = self.env["ai.view.context"]

    def test_update_context_creates_record(self):
        self.ctx_model.update_context(
            model="account.move", viewType="list",
            domain=[["state", "=", "posted"]],
        )
        ctx = self.ctx_model.get_current_context()
        self.assertEqual(ctx.get("model"), "account.move")
        self.assertEqual(ctx.get("view_type"), "list")

    def test_update_context_updates_existing(self):
        self.ctx_model.update_context(
            model="account.move", viewType="list",
        )
        self.ctx_model.update_context(
            model="res.partner", viewType="form", recordId=1,
        )
        ctx = self.ctx_model.get_current_context()
        self.assertEqual(ctx.get("model"), "res.partner")
        self.assertEqual(ctx.get("view_type"), "form")
        self.assertEqual(ctx.get("record_id"), 1)

    def test_get_current_context_empty(self):
        self.ctx_model.search(
            [("user_id", "=", self.env.uid)]
        ).unlink()
        ctx = self.ctx_model.get_current_context()
        self.assertEqual(ctx, {})

    def test_track_web_search_read(self):
        self.env["account.move"].web_search_read(
            [], {"display_name": {}}, limit=5,
        )
        ctx = self.ctx_model.get_current_context()
        self.assertEqual(ctx.get("model"), "account.move")
        self.assertEqual(ctx.get("view_type"), "list")

    def test_track_web_read(self):
        partner = self.env["res.partner"].create({"name": "Test"})
        partner.web_read({"display_name": {}})
        ctx = self.ctx_model.get_current_context()
        self.assertEqual(ctx.get("model"), "res.partner")
        self.assertEqual(ctx.get("view_type"), "form")

    def test_track_ignores_unrelated(self):
        self.env["res.partner"].search_count([])
        ctx = self.ctx_model.get_current_context()
        self.assertNotEqual(ctx.get("view_type"), "list")

    def test_read_current_view_list(self):
        self.ctx_model.update_context(
            model="res.partner", viewType="list", domain=[],
        )
        result = self.env["ai.tool"]._ai_read_current_view()
        self.assertEqual(result.get("view_type"), "list")
        self.assertEqual(result.get("model"), "res.partner")
        self.assertIn("total_count", result)
        self.assertIn("records", result)

    def test_read_current_view_form(self):
        partner = self.env["res.partner"].create({"name": "Test Form"})
        self.ctx_model.update_context(
            model="res.partner", viewType="form", recordId=partner.id,
        )
        result = self.env["ai.tool"]._ai_read_current_view()
        self.assertEqual(result.get("view_type"), "form")
        self.assertEqual(result.get("record_id"), partner.id)

    def test_read_current_view_no_context(self):
        self.ctx_model.search(
            [("user_id", "=", self.env.uid)]
        ).unlink()
        result = self.env["ai.tool"]._ai_read_current_view()
        self.assertIn("error", result)

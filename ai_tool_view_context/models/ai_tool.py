# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.ai_tool.tools import aitool


class AiTool(models.Model):
    _inherit = "ai.tool"

    @aitool(
        input_schema={},
        output_schema={
            "view_type": {"type": "string"},
            "model": {"type": "string"},
            "total_count": {"type": "integer"},
            "records": {"type": "array"},
            "error": {"type": "string"},
        },
    )
    def _ai_read_current_view(self):
        """[ALWAYS CALL THIS FIRST when the user asks what they are viewing,
        what screen they are on, or to analyze their current view. Do NOT
        guess — call this tool. It returns exactly what the user sees:
        model, view type, records, domain, groupby.]

        Returns the user's current screen context with actual data.
        For list views: returns matching records.
        For form views: returns the full record with AI context.
        For pivot/graph: returns grouped data.
        """
        ctx = self.env["ai.view.context"].get_current_context()
        if not ctx.get("model"):
            return {
                "error": (
                    "No view context available. Ask the user: "
                    "'What model/screen are you viewing?'"
                )
            }
        model = ctx["model"]
        view_type = ctx.get("view_type", "list")
        domain = ctx.get("domain") or []
        record_id = ctx.get("record_id") or 0
        groupby = ctx.get("groupby") or []

        try:
            Model = self.env[model]
        except KeyError:
            return {"error": f"Model '{model}' not found"}

        if view_type == "form" and record_id:
            record = Model.browse(int(record_id)).exists()
            if not record:
                return {"error": f"Record {model}({record_id}) not found"}
            vals = record.read([])[0]
            try:
                ai_ctx = record._get_ai_context()
            except Exception:
                ai_ctx = ""
            return {
                "view_type": "form",
                "model": model,
                "record_id": record.id,
                "total_count": 1,
                "context": ai_ctx or str(vals),
                "records": [vals],
            }

        if view_type == "pivot" and groupby:
            groups = Model.web_read_group(
                domain, [], groupby, limit=10,
            )
            return {
                "view_type": "pivot",
                "model": model,
                "domain": domain,
                "groupby": groupby,
                "groups": groups,
            }

        total = Model.search_count(domain)
        records = Model.search_read(domain, ["display_name"], limit=10)
        return {
            "view_type": view_type,
            "model": model,
            "total_count": total,
            "records": records,
        }

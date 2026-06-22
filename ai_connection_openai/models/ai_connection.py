# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AiConnection(models.Model):
    _inherit = "ai.connection"

    kind = fields.Selection(
        selection_add=[("openai", "OpenAI")],
        ondelete={"openai": "cascade"},
    )

    def _get_client_openai(self, tools):
        self.ensure_one()
        return self._get_client_base_openai(tools)

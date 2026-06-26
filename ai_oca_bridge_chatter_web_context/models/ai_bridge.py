# Copyright 2025 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AiBridge(models.Model):
    _inherit = "ai.bridge"

    def _prepare_payload_chatter(self, record=None, **kwargs):
        payload = super()._prepare_payload_chatter(record=record, **kwargs)
        view_context = self.env.context.get("ai_view_context")
        if view_context:
            payload["view_context"] = view_context
        return payload

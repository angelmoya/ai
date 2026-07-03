# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailChannel(models.Model):
    _inherit = "discuss.channel"

    def _build_channel_prompt(self, message, thread, agent):
        parts = []
        record_context = self._get_channel_record_context(message)
        if record_context:
            parts.append(record_context)
        view_context = self._get_view_context_prompt()
        if view_context:
            parts.append(view_context)
        channel_history = self._get_channel_history(message)
        if channel_history:
            parts.append(channel_history)
        body = message.body or ""
        if message.attachment_ids:
            attachment_names = ", ".join(
                message.attachment_ids.mapped("name") or ["unknown"]
            )
            body = f"{body}\n\n[Attachments: {attachment_names}]"
        parts.append(body)
        return "\n\n".join(parts)

    def _get_view_context_prompt(self):
        vc = self.env.context.get("ai_view_context")
        if not vc:
            return ""
        if vc.get("model") in ("discuss.channel", "mail.channel"):
            return ""
        lines = ["## View Context"]
        if vc.get("model"):
            lines.append(f"- **Model**: {vc['model']}")
        if vc.get("view_type"):
            lines.append(f"- **View Type**: {vc['view_type']}")
        if vc.get("active_id"):
            lines.append(f"- **Active Record ID**: {vc['active_id']}")
        if vc.get("active_ids"):
            lines.append(f"- **Active Record IDs**: {vc['active_ids']}")
        if vc.get("domain"):
            lines.append(f"- **Domain**: {vc['domain']}")
        if vc.get("view_id"):
            lines.append(f"- **View ID**: {vc['view_id']}")
        return "\n".join(lines)

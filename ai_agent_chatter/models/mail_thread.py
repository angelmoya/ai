# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_post(self, **kwargs):
        if self.env.context.get("ai_no_agent_trigger"):
            return super().message_post(**kwargs)
        message = super().message_post(**kwargs)
        if message.author_id.user_ids.agent_id:
            return message
        ai_agents = self._get_mentioned_ai_agents(message)
        for user, agent in ai_agents:
            thread = agent._get_or_create_thread(user=message.author_id.user_ids[:1])
            prompt = self._build_thread_prompt(message)
            files = self._build_ai_files(message)
            agent.run(
                prompt=prompt,
                thread=thread,
                user=message.author_id.user_ids[:1] or self.env.user,
                files=files,
            )
            result = (
                thread.message_history[-1]["content"]
                if thread.message_history
                else ""
            )
            self.message_post(
                body=result,
                author_id=user.partner_id.id,
                subtype_xmlid="mail.mt_note" if kwargs.get("subtype_xmlid") == "mail.mt_note" else "mail.mt_comment",
            )
        return message

    def _get_mentioned_ai_agents(self, message):
        if not message.partner_ids:
            return []
        result = []
        for partner in message.partner_ids:
            for user in partner.user_ids.filtered("agent_id"):
                result.append((user, user.agent_id))
        return result

    def _build_thread_prompt(self, message):
        parts = []
        record_context = self._get_record_context()
        if record_context:
            parts.append(f"## Current Document\n\n{record_context}")
        record_history = self._get_record_history(message)
        if record_history:
            parts.append(record_history)
        body = message.body or ""
        if message.attachment_ids:
            attachment_names = ", ".join(
                message.attachment_ids.mapped("name") or ["unknown"]
            )
            body = f"{body}\n\n[Attachments: {attachment_names}]"
        parts.append(body)
        return "\n\n".join(parts)

    def _get_record_context(self):
        if not self or not hasattr(self, "_get_ai_context"):
            return None
        return self._get_ai_context()

    def _get_record_history(self, message, limit=10):
        ai_partners = self.env["res.partner"].search(
            [("user_ids.agent_id", "!=", False)]
        )
        ai_partner_ids = ai_partners.ids
        record_msgs = self.env["mail.message"].search(
            [
                ("model", "=", self._name),
                ("res_id", "=", self.id),
                ("id", "<", message.id),
            ],
            order="date asc",
            limit=limit,
        )
        if not record_msgs:
            return ""
        lines = []
        for msg in record_msgs:
            role = "assistant" if msg.author_id.id in ai_partner_ids else "user"
            author = msg.author_id.name or "Unknown"
            body = msg.body or ""
            lines.append(f"{role} ({author}): {body}")
        return "## Conversation History\n\n" + "\n".join(lines)

    def _build_ai_files(self, message):
        if not message.attachment_ids:
            return None
        files = []
        for att in message.attachment_ids:
            file_data = att._to_ai_file()
            if file_data.get("data"):
                files.append(file_data)
        return files or None

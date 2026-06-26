# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailChannel(models.Model):
    _inherit = "discuss.channel"

    def message_post(self, **kwargs):
        message = super().message_post(**kwargs)
        if message.author_id.user_ids.agent_id:
            return message
        channel_members = self.sudo().channel_member_ids
        ai_recipients = channel_members.filtered(
            lambda r: r.partner_id != message.author_id
            and r.partner_id.user_ids
            and r.partner_id.user_ids.agent_id
            and self._eligibile_for_ai(message, r)
        )
        for recipient in ai_recipients:
            recipient._notify_typing(is_typing=True)
            for user in recipient.partner_id.user_ids.filtered("agent_id"):
                agent = user.agent_id
                try:
                    thread = agent._get_or_create_thread(
                        user=message.author_id.user_ids[:1] or self.env.user,
                        channel=self,
                    )
                    prompt = self._build_channel_prompt(message, thread, agent)
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
                        message_type="comment",
                    )
                finally:
                    recipient._notify_typing(is_typing=False)
        return message

    def _eligibile_for_ai(self, message, recipient):
        if len(self.sudo().channel_member_ids) <= 2:
            return True
        if recipient.partner_id in message.partner_ids:
            return True
        return False

    def _build_channel_prompt(self, message, thread, agent):
        parts = []
        record_context = self._get_channel_record_context(message)
        if record_context:
            parts.append(record_context)
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

    def _get_channel_record_context(self, message):
        if not message.model or not message.res_id:
            return None
        if message.model == "discuss.channel":
            return None
        record = (
            self.env[message.model].browse(message.res_id).exists()
        )
        if not record:
            return None
        ctx = record._get_ai_context()
        if not ctx:
            return None
        return f"## Current Document\n\n{ctx}"

    def _get_channel_history(self, message, limit=20):
        ai_partner_ids = (
            self.sudo()
            .channel_member_ids.filtered(
                lambda m: m.partner_id.user_ids.agent_id
            )
            .partner_id.ids
        )
        channel_msgs = self.env["mail.message"].search(
            [
                ("model", "=", "discuss.channel"),
                ("res_id", "=", self.id),
                ("id", "<", message.id),
            ],
            order="date asc",
            limit=limit,
        )
        if not channel_msgs:
            return ""
        lines = []
        for msg in channel_msgs:
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

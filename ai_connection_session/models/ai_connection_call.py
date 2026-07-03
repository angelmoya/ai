# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import time
import traceback

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class AiConnectionCall(models.Model):
    _name = "ai.connection.call"
    _description = "AI Connection Call"
    _order = "id desc"

    connection_id = fields.Many2one(
        "ai.connection",
        required=True,
        ondelete="cascade",
        string="Connection",
    )
    session_id = fields.Many2one(
        "ai.connection.session",
        ondelete="set null",
        string="Session",
    )
    prompt = fields.Text(required=True)
    files = fields.Json(string="Files", default=None)
    tool_ids = fields.Many2many("ai.tool", string="Tools")
    context = fields.Text(string="System Context")
    response = fields.Text(readonly=True)
    tool_calls = fields.Json(readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("processing", "Processing"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
    )
    error = fields.Text(readonly=True)
    prompt_tokens = fields.Integer(readonly=True)
    completion_tokens = fields.Integer(readonly=True)
    total_tokens = fields.Integer(readonly=True)
    duration = fields.Float(readonly=True, string="Duration (s)")
    model_used = fields.Char(readonly=True)

    def _execute(self, max_iterations=10, **kwargs):
        self.ensure_one()
        self.write({"state": "processing"})
        start_time = time.time()
        connection = self.connection_id

        try:
            skills_context = connection._get_skills_context()
            system_parts = []
            if skills_context:
                system_parts.append(skills_context)
            if self.context:
                system_parts.append(self.context)
            system_content = "\n\n".join(system_parts) if system_parts else ""

            session = self.session_id
            user_msg = {"role": "user", "content": self.prompt}
            if self.files:
                user_msg["files"] = self.files
            if session:
                messages = list(session.message_history or [])
                if system_content:
                    messages.append({"role": "system", "content": system_content})
                messages.append(user_msg)
            else:
                messages = []
                if system_content:
                    messages.append({"role": "system", "content": system_content})
                messages.append(user_msg)

            tools_to_use = self.tool_ids if self.tool_ids else connection.tool_ids
            if not tools_to_use:
                tools_to_use = None
            client = getattr(
                connection, f"_get_client_{connection.kind}"
            )(tools_to_use)

            accumulated_prompt_tokens = 0
            accumulated_completion_tokens = 0
            iteration = 0
            message = {}
            first_tool_calls = None

            while iteration < max_iterations:
                iteration += 1

                parsed = client.handle_message(messages=messages)
                message = parsed["message"]
                usage = parsed.get("usage", {})

                accumulated_prompt_tokens += usage.get("prompt_tokens", 0)
                accumulated_completion_tokens += usage.get("completion_tokens", 0)

                tool_calls = parsed.get("tool_calls") or []
                if iteration == 1 and tool_calls:
                    first_tool_calls = tool_calls

                if not tool_calls:
                    break

                tool_results = self._execute_tool_calls(tool_calls)
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.get("content") or "",
                        "tool_calls": [
                            {
                                "id": tc.get("id", f"call_{i}"),
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": json.dumps(tc["arguments"]),
                                },
                            }
                            for i, tc in enumerate(tool_calls)
                        ],
                    }
                )
                messages.extend(tool_results)

            if session:
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.get("content", "") if message else "",
                    }
                )
                session.message_history = messages

            self.write(
                {
                    "response": message.get("content", "") if message else "",
                    "tool_calls": first_tool_calls,
                    "prompt_tokens": accumulated_prompt_tokens,
                    "completion_tokens": accumulated_completion_tokens,
                    "total_tokens": accumulated_prompt_tokens
                    + accumulated_completion_tokens,
                    "model_used": message.get("model", connection.model),
                    "state": "done",
                    "duration": time.time() - start_time,
                }
            )
        except Exception:
            self.write(
                {
                    "state": "error",
                    "error": traceback.format_exc(),
                    "duration": time.time() - start_time,
                }
            )
        return self

    def _execute_tool_calls(self, tool_calls):
        self.ensure_one()
        results = []
        for tc in tool_calls:
            name = tc["name"]
            arguments = tc["arguments"]
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    pass
            try:
                output = self._execute_tool_call(name, arguments)
                content = json.dumps(output) if output else "done"
            except ValueError as e:
                _logger.warning("Tool call failed: %s", e)
                content = f"Error: {e}"
            results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": content,
                }
            )
        return results

    def _execute_tool_call(self, tool_name, tool_args):
        self.ensure_one()
        tools = self.tool_ids if self.tool_ids else self.connection_id.tool_ids
        tool = tools.filtered(lambda t: t.name == tool_name)
        if not tool:
            raise ValueError(_("Tool %s not found.", tool_name))
        return tool._execute_tool(**tool_args)

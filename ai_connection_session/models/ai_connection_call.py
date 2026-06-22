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
    context = fields.Text(string="System Context")
    response = fields.Text(readonly=True)
    tool_calls = fields.Json(readonly=True, string="Tool Calls")
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
    prompt_tokens = fields.Integer(readonly=True, string="Prompt Tokens")
    completion_tokens = fields.Integer(readonly=True, string="Completion Tokens")
    total_tokens = fields.Integer(readonly=True, string="Total Tokens")
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
            if session:
                messages = list(session.message_history or [])
                if system_content:
                    messages.append({"role": "system", "content": system_content})
                messages.append({"role": "user", "content": self.prompt})
            else:
                messages = []
                if system_content:
                    messages.append({"role": "system", "content": system_content})
                messages.append({"role": "user", "content": self.prompt})

            tools_to_use = connection.tool_ids if connection.tool_ids else None
            client = getattr(connection, f"_get_client_{connection.kind}")(tools_to_use)

            accumulated_prompt_tokens = 0
            accumulated_completion_tokens = 0
            iteration = 0
            message = {}
            parsed = None
            first_tool_calls = None

            while iteration < max_iterations:
                iteration += 1

                raw = client._send_request(client._build_payload(messages))
                parsed = client._parse_response(raw)
                message = parsed["message"]
                usage = parsed.get("usage", {})

                accumulated_prompt_tokens += usage.get("prompt_tokens", 0)
                accumulated_completion_tokens += usage.get("completion_tokens", 0)

                if iteration == 1 and parsed.get("tool_calls"):
                    first_tool_calls = parsed["tool_calls"]

                if not parsed.get("tool_calls"):
                    break

                tool_calls = parsed["tool_calls"]
                tool_results = self._execute_tool_calls(tool_calls)

                messages.append(
                    {
                        "role": "assistant",
                        "content": message.get("content") or "",
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": tc["type"],
                                "function": {
                                    "name": tc["function"]["name"],
                                    "arguments": json.dumps(
                                        tc["function"]["arguments"]
                                    ),
                                },
                            }
                            for tc in tool_calls
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
                    "model_used": parsed.get("model") or connection.model,
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
            name = tc["function"]["name"]
            arguments = tc["function"]["arguments"]
            try:
                output = self._execute_tool_call(name, arguments)
                content = json.dumps(output) if output else "done"
            except ValueError as e:
                _logger.warning("Tool call failed: %s", e)
                content = f"Error: {e}"
            results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": content,
                }
            )
        return results

    def _execute_tool_call(self, tool_name, tool_args):
        self.ensure_one()
        tool = self.connection_id.tool_ids.filtered(lambda t: t.name == tool_name)
        if not tool:
            raise ValueError(_("Tool %s not found.", tool_name))
        return tool._execute_tool(**tool_args)

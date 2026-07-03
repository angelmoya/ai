import json
import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class AiConnection(models.Model):
    _inherit = "ai.connection"

    def _run_stream(self, prompt, tools=None, system_prompt="", max_iterations=10, files=None, session=None):
        """Generator that yields events as the agent processes.

        Yields dict events:
            {"type": "thinking", "iteration": int}
            {"type": "tool_call", "name": str, "arguments": dict}
            {"type": "tool_result", "name": str, "success": bool, "result": any}
            {"type": "done", "content": str, "usage": dict, "model": str, "first_tool_calls": list}
            {"type": "error", "message": str}
        """
        self.ensure_one()

        skills_context = self._get_skills_context()
        system_parts = []
        if skills_context:
            system_parts.append(skills_context)
        if system_prompt:
            system_parts.append(system_prompt)
        system_content = "\n\n".join(system_parts) if system_parts else ""

        if session and session.message_history:
            messages = list(session.message_history)
            if system_content:
                messages.insert(0, {"role": "system", "content": system_content})
        else:
            messages = []
            if system_content:
                messages.append({"role": "system", "content": system_content})

        user_msg = {"role": "user", "content": prompt}
        if files:
            user_msg["files"] = files
        messages.append(user_msg)

        if not tools:
            tools = self.tool_ids

        client = getattr(self, f"_get_client_{self.kind}")(tools)

        accumulated_prompt_tokens = 0
        accumulated_completion_tokens = 0
        iteration = 0
        last_message = {}
        first_tool_calls = None

        while iteration < max_iterations:
            iteration += 1
            yield {"type": "thinking", "iteration": iteration}

            try:
                parsed = client.handle_message(messages=messages, temperature=self.temperature)
            except Exception as e:
                _logger.exception("LLM call failed at iteration %s", iteration)
                yield {"type": "error", "message": str(e)}
                return

            last_message = parsed["message"]
            usage = parsed.get("usage", {})

            accumulated_prompt_tokens += usage.get("prompt_tokens", 0)
            accumulated_completion_tokens += usage.get("completion_tokens", 0)

            tool_calls = parsed.get("tool_calls") or []
            if iteration == 1 and tool_calls:
                first_tool_calls = tool_calls

            if not tool_calls:
                content = last_message.get("content", "")
                yield {
                    "type": "done",
                    "content": content,
                    "usage": {
                        "prompt_tokens": accumulated_prompt_tokens,
                        "completion_tokens": accumulated_completion_tokens,
                        "total_tokens": accumulated_prompt_tokens + accumulated_completion_tokens,
                    },
                    "model": last_message.get("model", self.model),
                    "first_tool_calls": first_tool_calls,
                }
                return

            messages.append({
                "role": "assistant",
                "content": last_message.get("content") or "",
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
            })

            for tc in tool_calls:
                name = tc["name"]
                arguments = tc["arguments"]
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        pass

                yield {"type": "tool_call", "name": name, "arguments": arguments}

                try:
                    tool = tools.filtered(lambda t: t.name == name)
                    if not tool:
                        raise ValueError(_("Tool %s not found.", name))
                    result = tool._execute_tool(**arguments)
                    content = json.dumps(result) if result else "done"
                    yield {"type": "tool_result", "name": name, "success": True, "result": result}
                except Exception as e:
                    _logger.warning("Tool call failed: %s", e)
                    content = f"Error: {e}"
                    yield {"type": "tool_result", "name": name, "success": False, "result": str(e)}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": content,
                })

        content = last_message.get("content", "") if last_message else ""
        yield {
            "type": "done",
            "content": content,
            "usage": {
                "prompt_tokens": accumulated_prompt_tokens,
                "completion_tokens": accumulated_completion_tokens,
                "total_tokens": accumulated_prompt_tokens + accumulated_completion_tokens,
            },
            "model": last_message.get("model", self.model) if last_message else self.model,
            "first_tool_calls": first_tool_calls,
        }

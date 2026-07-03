import json
import logging
import queue as queue_module
import threading

import markdown
from markupsafe import Markup

from odoo import http
from odoo.api import Environment
from odoo.sql_db import db_connect

_logger = logging.getLogger(__name__)


def _md_to_html(text):
    """Convert markdown text to sanitized HTML."""
    if not text:
        return ""
    html = markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br", "sane_lists"],
    )
    return Markup(html)


class StreamController(http.Controller):

    @http.route("/ai/stream/", type="http", auth="user", csrf=False, methods=["POST"])
    def stream(self, **kwargs):
        raw = http.request.get_json_data()
        prompt = raw.get("prompt", "")
        message_id = raw.get("message_id")
        model = raw.get("model", "")
        res_id = raw.get("res_id")
        partner_ids = raw.get("partner_ids", [])
        subtype_xmlid = raw.get("subtype_xmlid", "mail.mt_comment")

        if not model or not res_id or (not message_id and not prompt):
            return http.Response(
                json.dumps({"error": "model, res_id, and (message_id or prompt) are required"}),
                status=400,
                content_type="application/json",
            )

        record = http.request.env[model].browse(res_id)
        if not record.exists():
            return http.Response(
                json.dumps({"error": "Record not found"}),
                status=404,
                content_type="application/json",
            )

        is_channel = model == "discuss.channel"

        if message_id:
            user_message = http.request.env["mail.message"].browse(message_id)
            if not user_message.exists():
                return http.Response(
                    json.dumps({"error": "Message not found"}),
                    status=404,
                    content_type="application/json",
                )
        else:
            user_message = record.with_context(ai_no_agent_trigger=True).message_post(
                body=prompt,
                body_is_html=True,
                message_type="comment",
                partner_ids=partner_ids,
                subtype_xmlid=subtype_xmlid,
            )
            http.request.env.cr.commit()

        if is_channel:
            ai_agents = record._get_channel_ai_agents(user_message)
        else:
            ai_agents = record._get_mentioned_ai_agents(user_message)
        if not ai_agents:
            return http.Response(
                json.dumps({"error": "No AI agents found for mentioned partners"}),
                status=400,
                content_type="application/json",
            )

        event_queue = queue_module.Queue()

        db_name = http.request.env.cr.dbname
        uid = http.request.env.uid
        context = dict(http.request.env.context)

        def run_agent(user_id, agent_id, msg_id):
            try:
                db = db_connect(db_name)
                cr = db.cursor()
                try:
                    env = Environment(cr, uid, context)
                    user = env["res.users"].browse(user_id)
                    agent = env["ai.agent"].browse(agent_id)
                    connection = agent.connection_id
                    if not connection:
                        event_queue.put({"type": "error", "message": "Agent has no connection"})
                        event_queue.put(None)
                        return

                    record_env = env[model].browse(res_id)
                    message_env = env["mail.message"].browse(msg_id)

                    if model == "discuss.channel":
                        full_prompt = record_env._build_channel_prompt(message_env, None, None)
                    else:
                        full_prompt = record_env._build_thread_prompt(message_env)
                    files = record_env._build_ai_files(message_env)

                    thread_env = agent.with_env(env)
                    thread = thread_env._get_or_create_thread(user=user)
                    system_prompt = thread_env._build_system_prompt()

                    def post_note(text):
                        record_env.with_context(ai_no_agent_trigger=True).message_post(
                            body=text,
                            body_is_html=True,
                            message_type="comment",
                            author_id=user.partner_id.id,
                            subtype_xmlid="mail.mt_note",
                        )
                        cr.commit()

                    for event in connection._run_stream(
                        prompt=full_prompt,
                        tools=thread_env.tool_ids,
                        system_prompt=system_prompt,
                        session=thread.session_id,
                        files=files,
                    ):
                        event_queue.put(event)
                        if event["type"] == "thinking":
                            post_note(
                                f"<em>Thinking (iteration {event['iteration']})…</em>"
                            )

                        elif event["type"] == "tool_call":
                            name = event.get("name", "tool")
                            args = event.get("arguments") or {}
                            args_str = (
                                "<br/><small>" + json.dumps(args) + "</small>"
                                if args
                                else ""
                            )
                            post_note(
                                f"<em>Calling tool:</em> <strong>{name}</strong>{args_str}"
                            )

                        elif event["type"] == "tool_result":
                            name = event.get("name", "tool")
                            ok = event.get("success", False)
                            status = "✓ ok" if ok else "✗ failed"
                            result = event.get("result")
                            preview = ""
                            if result is not None:
                                preview = (
                                    result
                                    if isinstance(result, str)
                                    else json.dumps(result)
                                )
                                if len(preview) > 200:
                                    preview = preview[:200] + "…"
                                preview = "<br/><small>" + preview + "</small>"
                            post_note(
                                f"<em>{name}:</em> {status}{preview}"
                            )

                        elif event["type"] == "done":
                            content = event.get("content", "")
                            thread.message_history = list(
                                (thread.message_history or [])
                                + [
                                    {"role": "user", "content": full_prompt},
                                    {"role": "assistant", "content": content},
                                ]
                            )
                            record_env.with_context(ai_no_agent_trigger=True).message_post(
                                body=_md_to_html(content),
                                body_is_html=True,
                                message_type="comment",
                                author_id=user.partner_id.id,
                                subtype_xmlid=subtype_xmlid,
                            )
                            cr.commit()

                        elif event["type"] == "error":
                            error_msg = event.get("message", "Unknown error")
                            thread.message_history = list(
                                (thread.message_history or [])
                                + [
                                    {"role": "user", "content": full_prompt},
                                    {"role": "assistant", "content": f"Error: {error_msg}"},
                                ]
                            )
                            record_env.with_context(ai_no_agent_trigger=True).message_post(
                                body=f"<em>Error:</em> {error_msg}",
                                body_is_html=True,
                                message_type="comment",
                                author_id=user.partner_id.id,
                                subtype_xmlid=subtype_xmlid,
                            )
                            cr.commit()

                finally:
                    cr.close()
                event_queue.put(None)

            except Exception as e:
                _logger.exception("Background agent thread failed")
                event_queue.put({"type": "error", "message": str(e)})
                event_queue.put(None)

        first_user, first_agent = ai_agents[0]
        thread = threading.Thread(
            target=run_agent,
            args=(first_user.id, first_agent.id, user_message.id),
            daemon=True,
        )
        thread.start()

        def generate():
            while True:
                try:
                    event = event_queue.get(timeout=120)
                    if event is None:
                        break
                    yield f"data: {json.dumps(event)}\n\n"
                except queue_module.Empty:
                    yield f"data: {json.dumps({"type": "error", "message": "timeout"})}\n\n"
                    break

        return http.request.make_response(
            generate(),
            headers=[
                ("Content-Type", "text/event-stream"),
                ("Cache-Control", "no-cache"),
                ("Connection", "keep-alive"),
                ("X-Accel-Buffering", "no"),
            ],
        )

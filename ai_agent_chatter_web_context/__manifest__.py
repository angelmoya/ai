# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "AI Agent Chatter Web Context",
    "summary": "Enriches AI agent prompts with the active Odoo view context",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "SDi,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/ai",
    "depends": [
        "ai_agent_chatter",
        "mail",
    ],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "ai_agent_chatter_web_context/static/src/popup_chat_view_context.js",
        ],
    },
    "demo": [],
}

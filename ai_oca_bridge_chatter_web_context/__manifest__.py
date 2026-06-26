# Copyright 2025 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "AI OCA Bridge Chatter Web Context",
    "summary": "Enriches popup chat messages with the active Odoo view context",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Dixmit,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/ai",
    "depends": [
        "ai_oca_bridge_chatter",
    ],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "ai_oca_bridge_chatter_web_context/static/src/popup_chat_view_context.js",
        ],
    },
    "demo": [],
}

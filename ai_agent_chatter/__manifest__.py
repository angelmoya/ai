# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "AI Agent Chatter",
    "summary": "Integrate AI agents with Odoo discuss channels",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "SDi,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/ai",
    "depends": [
        "ai_agent",
        "mail",
    ],
    "data": [
        "views/res_users.xml",
        "views/ai_agent_thread.xml",
    ],
    "demo": [],
}

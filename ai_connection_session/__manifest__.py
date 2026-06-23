# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "AI Connection Session",
    "summary": """Session and call persistence for AI connections.""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "SDi,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/ai",
    "depends": [
        "ai_connection",
        "ai_tool",
        "ai_skill",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/ai_call_wizard.xml",
        "views/ai_connection_call.xml",
        "views/ai_connection_session.xml",
        "views/ai_connection.xml",
    ],
    "demo": [],
}

# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "AI Server Action",
    "summary": """Execute AI prompts from Odoo server actions.""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "SDi,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/ai",
    "depends": [
        "ai_connection",
        "ai_tool",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/ir_actions_server.xml",
    ],
    "demo": [],
}

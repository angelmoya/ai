# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "AI Tool Server Action",
    "summary": """Expose Odoo server actions as AI tools.""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "SDi,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/ai",
    "depends": [
        "ai_connection",
        "ai_tool",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/ai_tool_server_action_wizard.xml",
        "views/ai_tool.xml",
    ],
    "demo": [],
}

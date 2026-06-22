# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "AI Tool Web Fetch",
    "summary": """Web fetch tool for AI connections.""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "SDi,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/ai",
    "depends": [
        "ai_tool",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ai_tools.xml",
    ],
    "demo": [],
}

# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "AI Tool View Context",
    "summary": "Track user view context so AI agents know what the user sees",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "SDi,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/ai",
    "depends": [
        "ai_tool",
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ai_tool_data.xml",
    ],
    "demo": [],
}

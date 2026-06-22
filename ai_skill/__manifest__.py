# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "AI Skill",
    "summary": """
    AI Agent Skills for AI Connections.
    Stores and syncs skills from Agent Skills Standard.
    """,
    "version": "18.0.1.1.0",
    "license": "AGPL-3",
    "author": "SDi,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/ai",
    "category": "AI",
    "development_status": "Beta",
    "depends": [
        "mail",
        "ai_tool",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ai_skill_data.xml",
        "views/ai_skill_view.xml",
        "views/menu.xml",
        "views/ai_skill_category_view.xml",
    ],
    "demo": [],
}

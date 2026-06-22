# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "AI Agent Multi-User",
    "summary": """Multi-user access control for AI agents.""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "SDi,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/ai",
    "depends": [
        "ai_agent",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/ai_agent_access_rule.xml",
        "views/ai_agent.xml",
    ],
    "demo": [],
}

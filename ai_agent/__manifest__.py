# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "AI Agent",
    "summary": ("Autonomous AI agents with planning, protocols and per-user threads."),
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "SDi,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/ai",
    "depends": [
        "ai_connection_session",
        "ai_skill",
        "ai_tool",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/ai_agent_soul.xml",
        "views/ai_agent_protocol.xml",
        "views/ai_agent.xml",
        "views/ai_agent_thread.xml",
        "views/ai_agent_plan.xml",
        "views/ai_agent_job.xml",
        "views/ai_agent_run_wizard.xml",
        "views/menu.xml",
    ],
    "demo": [],
}

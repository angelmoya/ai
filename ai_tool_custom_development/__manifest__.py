{
    "name": "AI Tool Custom Development",
    "summary": "AI tools to create models, fields, views, and actions in Odoo.",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "SDi,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/ai",
    "depends": [
        "ai_tool",
        "ai_skill",
        "ai_agent",
        "ai_connection_openai",
        "ai_tool_view_context",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ai_tools.xml",
        "data/ai_skills.xml",
        "data/ai_protocols.xml",
        "data/ai_agents.xml",
    ],
    "demo": [],
}

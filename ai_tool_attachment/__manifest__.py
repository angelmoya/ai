# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "AI Tool Attachment",
    "summary": "Tool to read attachment content and pass files to AI connections",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "SDi,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/ai",
    "depends": [
        "ai_tool",
    ],
    "data": [
        "data/ai_tool_data.xml",
    ],
    "demo": [],
    "external_dependencies": {
        "python": [
            "PyPDF2",
        ],
    },
}

# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from odoo.addons.ai_tool.tools import aitool


class AiToolServerActionRunner(models.Model):
    _name = "ai.tool.server.action.runner"
    _description = "AI Tool Server Action Runner"
    _auto = False

    @aitool(
        input_schema={},
        output_schema={},
    )
    def _ai_server_action_wrapper(self, **kwargs):
        return {}

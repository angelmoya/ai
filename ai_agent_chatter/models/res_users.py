# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    agent_id = fields.Many2one(
        "ai.agent",
        string="AI Agent",
    )

    def _compute_im_status(self):
        for record in self.filtered("agent_id"):
            record.im_status = "online"
        to_process = self.filtered(lambda r: not r.agent_id)
        if not to_process:
            return
        return super(ResUsers, to_process)._compute_im_status()

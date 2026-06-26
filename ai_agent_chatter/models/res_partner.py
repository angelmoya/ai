# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _compute_im_status(self):
        for record in self.filtered("user_ids.agent_id"):
            record.im_status = "online"
        to_process = self.filtered(lambda r: not r.user_ids.agent_id)
        if not to_process:
            return
        return super(ResPartner, to_process)._compute_im_status()

import base64
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AiCustomExportController(http.Controller):

    @http.route(
        "/ai_custom_dev/export/<prefix>/download/<attachment_id>",
        type="http",
        auth="user",
    )
    def download_export(self, prefix, attachment_id):
        attachment = request.env["ir.attachment"].sudo().browse(int(attachment_id))
        if not attachment or not attachment.exists():
            return request.not_found()

        content = base64.b64decode(attachment.datas)

        return request.make_response(
            content,
            headers=[
                ("Content-Type", "application/zip"),
                (
                    "Content-Disposition",
                    f'attachment; filename="{prefix}_module.zip"',
                ),
            ],
        )

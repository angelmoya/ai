# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

import requests

from odoo import models

from odoo.addons.ai_tool.tools import aitool

_logger = logging.getLogger(__name__)


class AiToolWebFetch(models.Model):
    _inherit = "ai.tool"

    @aitool(
        input_schema={
            "url": {"type": "string", "description": "URL to fetch content from"},
        },
        required_inputs=["url"],
        output_schema={},
    )
    def _ai_web_fetch(self, url, **kwargs):
        """Fetch the content of a URL and return it as text."""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return {"content": response.text}
        except requests.exceptions.RequestException as e:
            _logger.warning("web_fetch failed: %s", e)
            return {"error": str(e)}

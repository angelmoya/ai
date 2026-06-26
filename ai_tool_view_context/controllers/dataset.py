# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.http import request

from odoo.addons.web.controllers.dataset import DataSet


class DataSetAi(DataSet):

    _IGNORED_MODELS = {
        "discuss.channel",
        "discuss.channel.member",
        "mail.message",
        "mail.followers",
        "mail.activity",
        "mail.compose.message",
        "bus.bus",
        "ir.attachment",
    }

    @http.route()
    def call_kw(self, model, method, args, kwargs, path=None):
        self._track_view_context(model, method, args, kwargs)
        return super().call_kw(model, method, args, kwargs, path=path)

    @classmethod
    def _track_view_context(cls, model, method, args, kwargs):
        if model in cls._IGNORED_MODELS:
            return
        if not args:
            args = []
        view_type = None
        domain = None
        record_id = None
        groupby = None

        if method == "web_search_read":
            view_type = "list"
            domain = args[0] if len(args) > 0 else []
        elif method == "web_read":
            view_type = "form"
            ids = args[0] if len(args) > 0 else []
            if isinstance(ids, list) and ids:
                record_id = ids[0]
        elif method == "web_read_group":
            view_type = "pivot"
            domain = args[0] if len(args) > 0 else []
            groupby = args[2] if len(args) > 2 else []
        elif method == "get_views":
            views = args[0] if len(args) > 0 else []
            if isinstance(views, list) and views and isinstance(views[0], list):
                view_type = views[0][1] if len(views[0]) > 1 else None
        else:
            return

        if not view_type:
            return

        try:
            request.env["ai.view.context"].update_context(
                model=model,
                viewType=view_type,
                domain=domain,
                recordId=record_id,
                groupby=groupby,
            )
        except Exception:
            pass

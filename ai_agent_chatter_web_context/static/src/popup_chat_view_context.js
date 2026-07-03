/** @odoo-module **/
// Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Composer.prototype, {
    setup() {
        super.setup();
        this._actionService = useService("action");
        try {
            this._searchService = useService("search");
        } catch (_) {
            this._searchService = null;
        }
    },

    get extraData() {
        const controller = this._actionService.currentController;
        if (!controller || controller.action?.type !== "ir.actions.act_window") {
            return super.extraData;
        }
        const action = controller.action;
        const currentState = controller.currentState || {};
        const actionCtx = action.context || {};

        const activeId = currentState.resId || actionCtx.active_id || undefined;
        const activeIds =
            actionCtx.active_ids ||
            (activeId ? [activeId] : []);

        let domain = action.domain || [];
        if (this._searchService?.searchModel?.query) {
            try {
                const sq = this._searchService.searchModel.query;
                domain = sq.getSearchDomain?.() || sq.getDomain?.() || sq.domain || domain;
            } catch (_) {}
        }

        const aiViewContext = {
            model: action.res_model,
            view_type: controller.props?.viewType,
            domain: domain,
            active_id: activeId,
            active_ids: activeIds,
        };
        if (controller.props?.view?.id) {
            aiViewContext.view_id = controller.props.view.id;
        }

        return {
            ...super.extraData,
            context: {
                ...(super.extraData?.context || {}),
                ai_view_context: aiViewContext,
            },
        };
    },
});

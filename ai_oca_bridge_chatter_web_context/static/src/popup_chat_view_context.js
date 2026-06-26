/** @odoo-module **/
// Copyright 2025 Dixmit
// License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Composer.prototype, {
    setup() {
        super.setup();
        this._actionService = useService("action");
    },

    get extraData() {
        if (!this.env.inChatWindow) {
            return super.extraData;
        }
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

        const aiViewContext = {
            model: action.res_model,
            view_type: controller.props?.viewType,
            domain: action.domain || [],
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

/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { toRaw } from "@odoo/owl";
import { streamAgentResponse } from "./stream_consumer.esm";

console.log("AI Stream: module loaded, patching Composer.sendMessage");

let progressPanel = null;

function getProgressPanel() {
    if (!progressPanel) {
        progressPanel = document.createElement("div");
        progressPanel.className = "o_ai_stream_progress";
        progressPanel.style.cssText =
            "position:fixed;bottom:80px;right:20px;width:380px;max-height:50vh;" +
            "background:#fff;border:1px solid #ddd;border-radius:8px;" +
            "box-shadow:0 4px 16px rgba(0,0,0,0.18);" +
            "z-index:10000;display:none;overflow-y:auto;font-size:13px;" +
            "font-family:system-ui,-apple-system,sans-serif;";
        progressPanel.innerHTML =
            '<div style="padding:10px 14px;background:#f5f5f5;border-bottom:1px solid #ddd;' +
            'font-weight:600;border-radius:8px 8px 0 0;display:flex;justify-content:space-between;' +
            'align-items:center;">' +
            '<span>AI Agent</span>' +
            '<button class="o_ai_stream_close" style="background:none;border:none;' +
            'cursor:pointer;font-size:16px;color:#666;padding:0;line-height:1;">&times;</button>' +
            "</div>" +
            '<div class="o_ai_stream_progress_body" style="padding:10px 14px;"></div>';
        document.body.appendChild(progressPanel);
        progressPanel.querySelector(".o_ai_stream_close").addEventListener(
            "click",
            () => {
                progressPanel.style.display = "none";
            }
        );
    }
    return progressPanel;
}

function resetPanelBody(panel) {
    const body = panel.querySelector(".o_ai_stream_progress_body");
    body.innerHTML = "";
    return body;
}

function appendLine(body, text, color) {
    const div = document.createElement("div");
    div.style.cssText = "padding:3px 0;display:flex;align-items:flex-start;gap:6px;";
    const marker = document.createElement("span");
    marker.style.cssText = `color:${color};font-weight:bold;flex-shrink:0;`;
    marker.textContent = "›";
    const txt = document.createElement("span");
    txt.style.cssText = `color:${color};word-break:break-word;`;
    txt.textContent = text;
    div.appendChild(marker);
    div.appendChild(txt);
    body.appendChild(div);
    body.parentElement.scrollTop = body.parentElement.scrollHeight;
}

function updateProgress(event) {
    const panel = getProgressPanel();
    const body = panel.querySelector(".o_ai_stream_progress_body");

    switch (event.type) {
        case "thinking":
            appendLine(body, `Thinking (iteration ${event.iteration})…`, "#666");
            break;
        case "tool_call": {
            const name = event.name || "tool";
            const args = event.arguments
                ? Object.keys(event.arguments).length
                    ? " " + JSON.stringify(event.arguments)
                    : ""
                : "";
            appendLine(body, `Calling tool: ${name}${args}`, "#1a7f37");
            break;
        }
        case "tool_result": {
            const name = event.name || "tool";
            const status = event.success ? "✓ ok" : "✗ failed";
            const preview = event.result
                ? (typeof event.result === "string"
                    ? event.result.slice(0, 120)
                    : JSON.stringify(event.result).slice(0, 120))
                : "";
            appendLine(body, `${name}: ${status}${preview ? " — " + preview : ""}`,
                event.success ? "#1a7f37" : "#cf222e");
            break;
        }
        case "done":
            appendLine(body, "Complete", "#1a7f37");
            setTimeout(() => {
                panel.style.display = "none";
            }, 3000);
            break;
        case "error":
            appendLine(body, `Error: ${event.message || "Unknown error"}`, "#cf222e");
            setTimeout(() => {
                panel.style.display = "none";
            }, 8000);
            break;
    }
}

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this._aiStreamNotification = useService("notification");
    },

    get extraData() {
        const result = super.extraData;
        if (this._aiStreamMode) {
            return {
                ...result,
                context: {
                    ...(result?.context || {}),
                    ai_no_agent_trigger: true,
                },
            };
        }
        return result;
    },

    async sendMessage() {
        const composer = toRaw(this.props.composer);
        if (composer.message) {
            return super.sendMessage();
        }
        const postData = this.postData;
        const partnerIds =
            postData?.partner_ids || composer.mentionedPartners?.map((p) => p.id) || [];
        const text = composer.text || "";
        const thread = this.thread;
        const notification = this._aiStreamNotification;

        console.log("AI Stream: sendMessage called", {
            text,
            partnerIds,
            threadModel: thread?.model,
            channelType: thread?.channel_type,
        });

        if (!text.trim() && !composer.attachments.length) {
            return super.sendMessage();
        }

        let allPartnerIds = [...partnerIds];
        if (thread?.channel_type === "chat") {
            let correspondentPartnerId;
            if (thread.correspondent?.persona?.id) {
                correspondentPartnerId = thread.correspondent.persona.id;
            } else if (thread.correspondent?.id) {
                correspondentPartnerId = thread.correspondent.id;
            } else if (thread.channelMembers?.length) {
                const selfId = this.store?.self?.id;
                const other = thread.channelMembers.find(
                    (m) => m.persona?.id && m.persona.id !== selfId
                );
                correspondentPartnerId = other?.persona?.id;
            }
            if (
                correspondentPartnerId &&
                !allPartnerIds.includes(correspondentPartnerId)
            ) {
                allPartnerIds.push(correspondentPartnerId);
            }
        }

        if (!allPartnerIds.length) {
            return super.sendMessage();
        }

        // Attachments: fall back to normal send (sync agent via message_post)
        if (composer.attachments.length) {
            if (notification) {
                notification.add("AI Agent processing (with attachments)…", {
                    type: "info",
                    title: "AI Agent",
                });
            }
            return super.sendMessage();
        }

        if (!this.state.active) {
            return;
        }
        this.state.active = false;

        const panel = getProgressPanel();
        resetPanelBody(panel);
        panel.style.display = "block";
        if (notification) {
            notification.add("AI Agent is thinking…", {
                type: "info",
                title: "AI Agent",
            });
        }

        // Phase 1: post the user message via the normal Discuss flow
        // This creates a pending message that appears immediately (outgoing,
        // green bubble) and gets confirmed by the server. ai_no_agent_trigger
        // prevents the synchronous agent call in message_post override.
        this._aiStreamMode = true;
        let userMessage;
        try {
            userMessage = await thread.post(text, postData, this.extraData);
        } catch (e) {
            this._aiStreamMode = false;
            console.warn("AI Stream: failed to post user message, falling back", e);
            panel.style.display = "none";
            this.state.active = true;
            return super.sendMessage();
        }
        this._aiStreamMode = false;

        // Phase 2: call the stream endpoint with the existing message ID.
        // The server uses the already-posted message to build the prompt and
        // posts the agent response as a new message.
        try {
            const result = await streamAgentResponse({
                messageId: userMessage.id,
                model: thread.model,
                resId: thread.id,
                partnerIds: allPartnerIds,
                onEvent: updateProgress,
            });
            console.log("AI Stream: stream completed", result);

            if (result.type === "error") {
                if (notification) {
                    notification.add(
                        "AI Agent error: " + (result.message || "Unknown error"),
                        { type: "danger", title: "AI Agent" }
                    );
                }
                return;
            }

            if (notification) {
                notification.add("AI Agent completed", {
                    type: "success",
                    title: "AI Agent",
                });
            }
        } catch (e) {
            console.warn("AI stream failed:", e);
            if (notification) {
                notification.add("AI stream failed: " + (e.message || e), {
                    type: "warning",
                    title: "AI Agent",
                });
            }
        } finally {
            // Always restore composer state — the user message is already
            // posted, so we just clear the local composer text/attachments.
            this.clear();
            if (this.props.onPostCallback) {
                this.props.onPostCallback();
            }
            this.state.active = true;
        }
    },
});

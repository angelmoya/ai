/** @odoo-module **/

export async function streamAgentResponse({
    prompt,
    messageId,
    model,
    resId,
    partnerIds,
    onEvent,
}) {
    const body = { model, res_id: resId, partner_ids: partnerIds };
    if (messageId) {
        body.message_id = messageId;
    } else if (prompt) {
        body.prompt = prompt;
    }

    const response = await fetch("/ai/stream/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    if (!response.ok) {
        const err = await response
            .json()
            .catch(() => ({ error: `HTTP ${response.status}` }));
        throw new Error(err.error || `HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
            if (line.startsWith("data: ")) {
                try {
                    const event = JSON.parse(line.slice(6));
                    onEvent(event);
                    if (event.type === "done" || event.type === "error") {
                        return event;
                    }
                } catch (e) {
                    console.error("SSE parse error:", e, "line:", line);
                }
            }
        }
    }
}

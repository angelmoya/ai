This module integrates AI agents with Odoo discuss channels.

Users can assign an AI agent to a `res.users` record, making the agent
appear as a chat participant. When a human posts a message in a channel
with an AI agent member:

- In direct chats (≤2 members), the agent auto-responds.
- In group channels, the agent responds only when @mentioned.
- The agent sees the document being discussed (via form view context).
- The agent sees recent conversation history for context.
- A typing indicator shows while the agent processes the request.
- AI agents do not respond to other AI agents (anti-loop).

No external HTTP bridge is needed — the agent calls its configured
`ai.connection` directly.

This module adds session and call persistence for AI connections, enabling multi-turn conversations and audit trails for AI interactions.

Key features:

- **ai.connection.session** model for multi-turn conversations with JSON message history and automatic context accumulation.
- **ai.connection.call** model for individual API calls with full tracking: prompt, response, tool calls, token usage, duration, and error state.
- **AI Call Wizard** (`ai.call.wizard`) provides a user-friendly form to execute prompts against a connection, optionally within a session.
- Adds `tool_ids` and `skill_ids` Many2many fields to connections for tool/skill selection per connection.
- Overrides `_get_skills_context()` to inject linked skill instructions as system context.
- Sessions maintain message history across calls, enabling coherent multi-turn conversations.
- Call records track prompt/completion tokens and support retry via the wizard.


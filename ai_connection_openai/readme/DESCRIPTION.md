This module provides an OpenAI provider for AI connections, enabling Odoo to connect to the OpenAI API for chat completions using models like GPT-4o.

Key features:

- Registers the `openai` connection kind.
- Uses the base OpenAI client from `ai_connection_base_openai` with OpenAI-specific defaults.
- Default endpoint is `https://api.openai.com/v1`.
- Supports all base OpenAI client features: API key authentication, function calling, configurable model, max tokens, and temperature.


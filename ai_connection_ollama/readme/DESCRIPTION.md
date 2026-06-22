This module provides an Ollama provider for AI connections, allowing Odoo to connect to local or remote Ollama instances for chat completions.

Key features:

- Registers the `ollama` connection kind.
- **AiConnectionOllamaClient** extends the base OpenAI client with Ollama-specific configuration.
- Default endpoint is `http://localhost:11434` (configurable per connection).
- Supports `ollama_options` JSON field for provider-specific settings like `num_ctx`, `num_predict`, etc., injected into the request payload via `_enrich_payload()`.
- Inherits all capabilities from the base OpenAI client: streaming, function calling, API key auth.


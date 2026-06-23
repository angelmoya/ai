This module provides an Ollama provider for AI connections, allowing Odoo to connect to local or remote Ollama instances for chat completions using the native `ollama` Python library.

Key features:

- Registers the `ollama` connection kind.
- **OllamaClient** implements the `AiConnectionClient` interface using the `ollama` library.
- Default endpoint is `http://localhost:11434` (configurable per connection).
- Supports `ollama_options` JSON field for provider-specific settings like `num_ctx`, `num_predict`, etc.
- Supports function calling (tools) via the Ollama API.

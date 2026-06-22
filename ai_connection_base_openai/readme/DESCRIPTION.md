This module provides an OpenAI-compatible HTTP client that can be reused by any OpenAI-compatible AI provider, including OpenAI, Ollama, vLLM, Together, Groq, and others.

Key features:

- **AiConnectionOpenAIClient** implements the `/v1/chat/completions` protocol with streaming and function calling support.
- Handles API key authentication via Bearer token headers.
- Converts **ai.tool** records into the OpenAI tools schema for function calling.
- Adds `kind` selection `base_openai` and fields for `api_key`, `max_tokens`, and `temperature` on the connection model.
- `_enrich_payload()` hook allows subclasses to inject provider-specific payload fields (e.g., Ollama options).
- `_get_client_base_openai()` method creates a client instance configured from the connection record.


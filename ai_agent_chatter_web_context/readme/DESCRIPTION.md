Enriches AI agent prompts with the active Odoo view context.

When a user sends a message to an AI agent via record chatter or discuss
channels, the agent receives not only the record's database values but also
the UI view context — what view type (form, list, kanban), what domain
filters are active, which records are selected, and what view layout is
being used.

This gives the AI agent awareness of *how* the user is viewing the data,
not just *what* data exists.

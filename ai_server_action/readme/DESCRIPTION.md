# AI Server Action

This module extends `ir.actions.server` with an AI execution state. It allows
Odoo server actions to call an `ai.connection`, optionally using `ai.tool`
records, and to post the result as a message, update a record field, or store
it in an evaluation context variable.

Use cases include cron jobs, automated actions and form buttons that need to
invoke an LLM.

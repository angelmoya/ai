# AI Tool Server Action

This module allows administrators to expose existing Odoo server actions as
`ai.tool` records that an LLM can call.

A wizard helps create a new `ai.tool` from a selected `ir.actions.server`. The
tool can then be assigned to agents and invoked during AI execution.

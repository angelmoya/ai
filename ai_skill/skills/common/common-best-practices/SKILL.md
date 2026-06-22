# Common Best Practices

Enforce SOLID principles, guard-clause style, function size limits, and
intention-revealing naming across all languages.

**Use when**: refactoring for readability, applying clean-code patterns, reviewing
naming conventions, or reducing function complexity.

## Rules

- Functions must be under 30 lines
- Use guard clauses to flatten nesting
- Names must reveal intent - avoid abbreviations
- One level of abstraction per function
- No side effects in constructors

## Triggers

- `*.py`, `*.ts`, `*.js`, `*.go`

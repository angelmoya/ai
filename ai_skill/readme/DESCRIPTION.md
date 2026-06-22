This module adds the ability to store and manage AI agent skills. Skills are markdown instructions that tell an AI model how to perform specific tasks, such as weather lookup, translation, or summarization.

Key features:

- Define **ai.skill** records with name, description, content, priority, and source.
- Organize skills into **ai.skill.category** records with hierarchical subcategories.
- Sync skills from `SKILL.md` files on disk via the **Sync from Disk** button, supporting both flat and categorized directory layouts.
- Skills can be linked to AI connections and are injected as system context during AI calls.
- Trigger metadata (file patterns, keywords) enables context-aware skill selection.
- Supports bundled, custom, and NPX-registry skill sources.


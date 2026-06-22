# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import os
import re

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skills")


class AiSkill(models.Model):
    _name = "ai.skill"
    _description = "AI Skill"
    _order = "category_id, name"

    name = fields.Char(required=True)
    description = fields.Text(translate=True)
    category_id = fields.Many2one(
        "ai.skill.category", string="Category", index=True, required=True
    )
    triggers = fields.Json(
        help="File patterns and keywords that trigger this skill. "
        "Format: {'file_match': ['*.ts', '*.tsx'], 'keywords': ['security', 'auth']}",
    )
    file_path = fields.Char(
        help="Relative path to the SKILL.md file in the skills directory.",
    )
    content = fields.Text(
        help="Cached content of the SKILL.md file.",
    )
    source = fields.Selection(
        [
            ("npx", "NPX Registry"),
            ("custom", "Custom"),
            ("bundled", "Bundled"),
        ],
        default="custom",
        required=True,
    )
    source_url = fields.Char(string="Source URL")
    priority = fields.Selection(
        [
            ("P0", "P0 - Critical"),
            ("P1", "P1 - Important"),
            ("P2", "P2 - Nice to have"),
        ],
        default="P1",
        required=True,
    )
    active = fields.Boolean(default=True)

    def _get_content(self):
        self.ensure_one()
        if self.content:
            return self.content
        if self.file_path:
            full_path = os.path.join(SKILLS_DIR, self.file_path)
            try:
                with open(full_path, encoding="utf-8") as f:
                    return f.read()
            except (OSError, FileNotFoundError):
                _logger.warning("Skill file not found: %s", full_path)
        return ""

    def action_view_content(self):
        self.ensure_one()
        content = self._get_content()
        return {
            "type": "ir.actions.act_window",
            "res_model": "ai.skill",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": {
                "default_content": content,
            },
        }

    @api.model
    def action_sync_from_disk(self):
        """Scan the skills directory and sync skills to database.

        Supports two directory layouts:
          - Categorized:   skills/<category>/<skill_name>/SKILL.md
          - Flat (npx):    skills/<skill_name>/SKILL.md
        """
        if not os.path.isdir(SKILLS_DIR):
            _logger.warning("Skills directory not found: %s", SKILLS_DIR)
            return False

        categories = self._get_or_create_categories()
        uncategorized = self.env.ref("ai_skill.ai_skill_category_uncategorized", False)
        synced = 0
        for root, _dirs, files in os.walk(SKILLS_DIR):
            for fname in files:
                if fname.lower() != "skill.md":
                    continue
                rel_path = os.path.relpath(os.path.join(root, fname), SKILLS_DIR)
                skill_data = self._parse_skill_md(os.path.join(root, fname))
                if not skill_data:
                    continue

                # Determine category and effective name
                parts = rel_path.split(os.sep)
                if len(parts) == 2:
                    # Flat: skills/<name>/SKILL.md
                    category = uncategorized
                elif len(parts) >= 3:
                    # Categorized: skills/<cat>/<name>/SKILL.md
                    category = categories.get(parts[0])
                else:
                    continue

                if not category:
                    _logger.warning("No category for %s, skipping", rel_path)
                    continue

                existing = self.search([("file_path", "=", rel_path)], limit=1)
                with open(os.path.join(root, fname), encoding="utf-8") as f:
                    content = f.read()
                vals = {
                    "name": skill_data["name"],
                    "description": skill_data.get("description", ""),
                    "category_id": category.id,
                    "file_path": rel_path,
                    "content": content,
                    "source": "npx",
                }
                if skill_data.get("triggers"):
                    vals["triggers"] = skill_data["triggers"]
                if existing:
                    existing.write(vals)
                else:
                    self.create(vals)
                synced += 1

        _logger.info("Synced %d skills from disk", synced)
        return synced

    @api.model
    def _get_or_create_categories(self):
        """Walk skills dir and create/return category mapping."""
        categories = {}
        if not os.path.isdir(SKILLS_DIR):
            return categories
        for entry in os.listdir(SKILLS_DIR):
            subdir = os.path.join(SKILLS_DIR, entry)
            if not os.path.isdir(subdir):
                continue
            cat = self.env["ai.skill.category"].search([("name", "=", entry)], limit=1)
            if not cat:
                cat = self.env["ai.skill.category"].create({"name": entry})
            categories[entry] = cat
        return categories

    @api.model
    def _parse_skill_md(self, filepath):
        """Parse a SKILL.md file and extract metadata (YAML frontmatter or markdown)."""
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
        except (OSError, FileNotFoundError):
            return None

        result = {}

        # Try YAML frontmatter first
        fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            import yaml

            try:
                fm = yaml.safe_load(fm_match.group(1))
                if isinstance(fm, dict):
                    result["name"] = fm.get("name", "")
                    result["description"] = fm.get("description", "")
            except yaml.YAMLError:
                _logger.warning("Invalid YAML front matter in %s", filepath)

        # Fallback: extract name from first H1
        if not result.get("name"):
            name_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            result["name"] = (
                name_match.group(1).strip()
                if name_match
                else os.path.basename(os.path.dirname(filepath))
            )

        # Fallback: extract description
        if not result.get("description"):
            desc_match = re.search(
                r"^##\s+Description\s*\n+(.+?)(?=\n##|\Z)",
                content,
                re.MULTILINE | re.DOTALL,
            )
            if not desc_match:
                desc_match = re.search(r"^\*\*(.+?)\*\*", content, re.MULTILINE)
            if desc_match:
                result["description"] = desc_match.group(1).strip()[:512]

        # Extract triggers from markdown body
        triggers = {"file_match": [], "keywords": []}
        for line in content.splitlines():
            line_lower = line.lower().strip()
            if re.match(r"^\*\s*`?\*\.\w+`?", line):
                match = re.search(r"`(\*\.\w+)`", line)
                if match:
                    triggers["file_match"].append(match.group(1))
            for kw in ["use when", "trigger", "keyword"]:
                if kw in line_lower:
                    continue
        result["triggers"] = triggers if any(triggers.values()) else None

        return result

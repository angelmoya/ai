# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AiSkillCategory(models.Model):
    _name = "ai.skill.category"
    _description = "AI Skill Category"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    parent_id = fields.Many2one(
        "ai.skill.category", string="Parent Category", index=True
    )
    child_ids = fields.One2many(
        "ai.skill.category", "parent_id", string="Subcategories"
    )
    skill_ids = fields.One2many("ai.skill", "category_id", string="Skills")
    skill_count = fields.Integer(compute="_compute_skill_count")

    def _compute_skill_count(self):
        for record in self:
            record.skill_count = len(record.skill_ids)

# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from xml.etree import ElementTree

from odoo import models

_logger = logging.getLogger(__name__)

_MAX_TABLE_ROWS = 50


class Base(models.AbstractModel):
    _inherit = "base"

    def _get_ai_context(self):
        self.ensure_one()
        view = self.get_view(view_type="form")
        arch = view.get("arch", "")
        fields_info = view.get("fields", {})
        if not arch:
            return ""
        tree = ElementTree.fromstring(arch)
        field_names = self._parse_view_fields(tree, fields_info)
        if not field_names:
            return ""
        data = self._read_ai_fields(field_names, self.ids[:1])
        return self._format_ai_context(data)

    def _parse_view_fields(self, node, fields_info):
        field_names = []
        model_fields = self.fields_get()
        for child in node:
            if child.tag == "field":
                name = child.attrib.get("name")
                if not name or name in field_names or name not in model_fields:
                    continue
                info = fields_info.get(name, {})
                if info.get("modifiers"):
                    try:
                        modifiers = (
                            info["modifiers"]
                            if isinstance(info["modifiers"], dict)
                            else eval(info["modifiers"])
                        )
                    except Exception:
                        modifiers = {}
                    if modifiers.get("invisible"):
                        continue
                field_names.append(name)
                field_type = info.get("type") or model_fields.get(name, {}).get("type", "")
                if field_type in ("one2many",):
                    sub_fields = self._parse_sub_view(child, fields_info)
                    field_names.append((name, sub_fields))
            field_names.extend(self._parse_view_fields(child, fields_info))
        return field_names

    def _parse_sub_view(self, node, fields_info):
        sub_fields = []
        for child in node:
            if child.tag in ("tree", "form"):
                sub_fields = self._parse_view_fields(child, fields_info)
                break
            sub_fields.extend(self._parse_sub_view(child, fields_info))
        return sub_fields

    def _read_ai_fields(self, field_names, ids):
        read_names = []
        one2many_fields = {}
        for name in field_names:
            if isinstance(name, tuple):
                read_names.append(name[0])
                one2many_fields[name[0]] = name[1]
            else:
                read_names.append(name)
        if not read_names:
            return {}
        vals = self.read(read_names)[0]
        for field_name, sub_fields in one2many_fields.items():
            records = self[field_name]
            if len(records) > _MAX_TABLE_ROWS:
                _logger.info(
                    "Truncating %s %s from %s to %s rows",
                    self._name,
                    field_name,
                    len(records),
                    _MAX_TABLE_ROWS,
                )
            vals[field_name] = [
                rec._read_ai_fields(sub_fields, rec.ids)
                for rec in records[:_MAX_TABLE_ROWS]
            ]
        return vals

    def _format_ai_context(self, data):
        lines = []
        for key, value in data.items():
            if key == "id":
                continue
            if isinstance(value, list) and value and isinstance(value[0], dict):
                lines.append(f"### {key}")
                lines.append(self._format_ai_table(value))
            elif isinstance(value, tuple):
                lines.append(f"- **{key}**: {value[1]} ({value[0]})")
            else:
                lines.append(f"- **{key}**: {value}")
        return "\n".join(lines)

    def _format_ai_table(self, rows):
        if not rows:
            return "_No records_"
        headers = list(rows[0].keys())
        header_line = "| " + " | ".join(headers) + " |"
        sep_line = "|" + "|".join(" --- " for _ in headers) + "|"
        data_lines = []
        for row in rows:
            values = [str(row.get(h, "")) for h in headers]
            data_lines.append("| " + " | ".join(values) + " |")
        return "\n".join([header_line, sep_line] + data_lines)

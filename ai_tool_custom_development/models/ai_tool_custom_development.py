import logging
from lxml import etree

from odoo import _, api, fields, models
from odoo.addons.ai_tool.tools import aitool
from odoo.exceptions import UserError
from odoo.addons.ai_tool_custom_development.models.export_helper import (
    CustomExportGenerator,
)

_logger = logging.getLogger(__name__)

FIELD_TYPE_MAP = {
    "char": "char",
    "text": "text",
    "html": "html",
    "integer": "integer",
    "float": "float",
    "boolean": "boolean",
    "date": "date",
    "datetime": "datetime",
    "binary": "binary",
    "selection": "selection",
    "many2one": "many2one",
    "one2many": "one2many",
    "many2many": "many2many",
    "monetary": "monetary",
}

class AiTool(models.Model):
    _inherit = "ai.tool"

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _check_prefix(self, prefix):
        if prefix and not prefix.replace("_", "").isalnum():
            raise UserError(
                _("Invalid prefix %r. Use only alphanumeric and underscores.")
                % prefix
            )

    def _field_type_to_odoo(self, field_type):
        return FIELD_TYPE_MAP.get(field_type)

    def _build_field_vals(self, model_id, prefix, name, field_type, **kw):
        self._check_prefix(prefix)
        ftype = self._field_type_to_odoo(field_type)
        if not ftype:
            raise UserError(_("Unsupported field type: %s") % field_type)

        field_name = f"x_{prefix}_{name}" if prefix else name
        vals = {
            "model_id": model_id,
            "name": field_name,
            "ttype": ftype,
            "field_description": kw.get("string") or name.replace("_", " ").title(),
            "required": kw.get("required", False),
            "index": kw.get("index", False),
            "readonly": kw.get("readonly", False),
            "translate": kw.get("translate", False),
            "store": True,
        }

        if kw.get("help"):
            vals["help"] = kw["help"]

        if ftype == "selection" and kw.get("selection"):
            parsed = self._parse_selection(kw["selection"])
            vals["selection"] = "\n".join(f"{k}:{v}" for k, v in parsed)

        if ftype in ("many2one", "one2many", "many2many"):
            if kw.get("relation"):
                vals["relation"] = kw["relation"]
        if ftype == "one2many" and kw.get("relation_field"):
            vals["relation_field"] = kw["relation_field"]
        if ftype == "many2many":
            if kw.get("relation_table"):
                vals["relation"] = kw["relation_table"]

        if ftype == "monetary" and kw.get("currency_field"):
            vals["currency_field"] = kw["currency_field"]

        if kw.get("tracking"):
            vals["tracking"] = 1

        if kw.get("default") is not None:
            vals["default_value"] = str(kw["default"])

        if kw.get("domain"):
            vals["domain"] = str(kw["domain"])

        return field_name, vals

    def _parse_selection(self, selection_str):
        result = []
        for part in selection_str.split(","):
            part = part.strip()
            if ":" in part:
                k, v = part.split(":", 1)
                result.append((k.strip(), v.strip()))
            else:
                result.append((part, part))
        return result

    def _parse_view_id(self, view_id_str):
        if isinstance(view_id_str, int):
            return view_id_str
        if view_id_str.isdigit():
            return int(view_id_str)
        module, _, xml_id = view_id_str.partition(".")
        if xml_id:
            record = self.env["ir.model.data"]._get(module, xml_id)
        else:
            record = self.env["ir.model.data"]._get("", view_id_str)
        return record.res_id

    def _resolve_view(self, view_id, view_type=None):
        if view_id:
            return self.env["ir.ui.view"].browse(self._parse_view_id(view_id))
        if not view_type:
            raise UserError(_("Provide a view_id or view_type to resolve a view."))
        model = self._context.get("default_model")
        if not model:
            raise UserError(_("No model context to resolve view by type."))
        view = self.env["ir.ui.view"].search(
            [("model", "=", model), ("type", "=", view_type)], limit=1
        )
        if not view:
            raise UserError(
                _("No %s view found for model %s.") % (view_type, model)
            )
        return view

    # ------------------------------------------------------------------
    # TOOL 10: get_model_views
    # ------------------------------------------------------------------

    @aitool(
        input_schema={
            "model": {"type": "string", "description": "Technical model name"},
            "view_type": {"type": "string", "enum": [
                "form", "list", "kanban", "search", "graph", "pivot",
                "calendar", "gantt", "activity", "cohort",
            ]},
        },
        required_inputs=["model"],
        output_schema={
            "views": {"type": "array", "items": {"type": "object", "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "type": {"type": "string"},
                "arch": {"type": "string"},
                "inherit": {"type": "boolean"},
            }}},
        },
    )
    def _ai_get_model_views(self, model, view_type=None, **kw):
        domain = [("model", "=", model)]
        if view_type:
            domain.append(("type", "=", view_type))
        views = self.env["ir.ui.view"].search(domain)
        result = []
        for v in views:
            result.append({
                "id": v.id,
                "name": v.name,
                "type": v.type,
                "arch": v.arch_db,
                "inherit": bool(v.inherit_id),
            })
        return {"views": result}

    # ------------------------------------------------------------------
    # TOOL 1: create_model
    # ------------------------------------------------------------------

    @aitool(
        input_schema={
            "prefix": {"type": "string"},
            "model_name": {"type": "string"},
            "fields": {"type": "array", "items": {"type": "object", "properties": {
                "name": {"type": "string"},
                "field_type": {"type": "string", "enum": [
                    "char", "text", "integer", "float", "boolean",
                    "date", "datetime", "selection", "many2one", "one2many",
                    "many2many", "monetary", "binary", "html",
                ]},
                "string": {"type": "string"},
                "required": {"type": "boolean"},
                "relation": {"type": "string"},
                "selection": {"type": "string"},
                "default": {"type": "string"},
                "tracking": {"type": "boolean"},
                "index": {"type": "boolean"},
                "help": {"type": "string"},
            }, "required": ["name", "field_type"]}},
        },
        required_inputs=["prefix", "model_name", "fields"],
        output_schema={
            "model": {"type": "string"},
            "model_id": {"type": "integer"},
            "fields_created": {"type": "array", "items": {"type": "string"}},
            "warning": {"type": "string"},
        },
    )
    def _ai_create_model(self, prefix, model_name, fields=None, **kw):
        self._check_prefix(prefix)
        model = f"x_{prefix}.{model_name}"
        display = kw.get("name") or model_name.replace("_", " ").title()

        if self.env["ir.model"].search([("model", "=", model)]):
            raise UserError(_("Model %s already exists.") % model)

        ir_model = self.env["ir.model"].create({
            "name": display,
            "model": model,
        })

        created = []
        for fdef in (fields or []):
            fdef_kw = {k: v for k, v in fdef.items()
                       if k not in ("name", "field_type")}
            fname, fvals = self._build_field_vals(
                ir_model.id, prefix, fdef["name"], fdef["field_type"], **fdef_kw
            )
            self.env["ir.model.fields"].create(fvals)
            created.append(fname)

        return {
            "model": model,
            "model_id": ir_model.id,
            "fields_created": created,
            "warning": _(
                "Model created without access rights. "
                "Call create_access_rights to grant permissions."
            ),
        }

    # ------------------------------------------------------------------
    # TOOL 2: create_field
    # ------------------------------------------------------------------

    @aitool(
        input_schema={
            "prefix": {"type": "string", "description": "Optional prefix (default: custom)"},
            "model": {"type": "string", "description": "Technical model name"},
            "name": {"type": "string", "description": "Field name (auto-prefixed)"},
            "field_type": {"type": "string", "enum": [
                "char", "text", "integer", "float", "boolean",
                "date", "datetime", "selection", "many2one", "one2many",
                "many2many", "monetary", "binary", "html",
            ]},
            "label": {"type": "string", "description": "Field label (alias for string)"},
            "string": {"type": "string"},
            "required": {"type": "boolean"},
            "relation": {"type": "string"},
            "selection": {"type": "string"},
            "default": {"type": "string"},
            "tracking": {"type": "boolean"},
            "index": {"type": "boolean"},
            "translate": {"type": "boolean"},
            "readonly": {"type": "boolean"},
            "help": {"type": "string"},
            "domain": {"type": "string"},
        },
        required_inputs=["model", "name", "field_type"],
        output_schema={
            "field_name": {"type": "string"},
            "field_id": {"type": "integer"},
            "model": {"type": "string"},
            "warning": {"type": "string"},
        },
    )
    def _ai_create_field(self, model, name, field_type, prefix=None, **kw):
        if prefix is None:
            prefix = "custom"
        if kw.get("label") and not kw.get("string"):
            kw["string"] = kw["label"]
        self._check_prefix(prefix)
        ir_model = self.env["ir.model"].search([("model", "=", model)], limit=1)
        if not ir_model:
            raise UserError(_("Model %s not found.") % model)

        full_name = f"x_{prefix}_{name}"
        existing = self.env["ir.model.fields"].search([
            ("model_id", "=", ir_model.id),
            ("name", "=", full_name),
        ], limit=1)
        if existing:
            raise UserError(
                _("Field %s already exists in model %s.") % (full_name, model)
            )

        warning = ""
        std_conflict = self.env["ir.model.fields"].search([
            ("model_id", "=", ir_model.id),
            ("name", "=like", name),
            ("ttype", "!=", False),
        ], limit=1)
        if std_conflict:
            warning = _(
                "Standard field '%s' exists in %s with similar name. "
                "Verify the user wants a custom field."
            ) % (std_conflict.name, model)

        _dummy, fvals = self._build_field_vals(ir_model.id, prefix, name, field_type, **kw)
        field = self.env["ir.model.fields"].create(fvals)

        return {
            "field_name": field.name,
            "field_id": field.id,
            "model": model,
            "warning": warning,
        }

    # ------------------------------------------------------------------
    # TOOL 3: add_field_to_view
    # ------------------------------------------------------------------

    @aitool(
        input_schema={
            "view_id": {"type": "string", "description": "DB ID or XML ID (optional if view_type+model given)"},
            "view_type": {"type": "string", "enum": [
                "form", "list", "kanban", "search", "graph", "pivot",
                "calendar", "gantt", "activity", "cohort",
            ], "description": "View type to resolve (default: form)"},
            "model": {"type": "string", "description": "Model name (e.g. account.move) required if view_type used"},
            "fields": {"type": "array", "items": {"type": "object", "properties": {
                "field_name": {"type": "string"},
                "position": {"type": "string", "enum": [
                    "after", "before", "inside", "replace", "attributes",
                ], "description": "before/after: insert relative to target. inside: insert inside target"},
                "target": {"type": "string", "description": "Field name or xpath expression for positioning"},
                "label": {"type": "string"},
                "widget": {"type": "string"},
                "nolabel": {"type": "boolean"},
                "placeholder": {"type": "string"},
                "attrs": {"type": "object"},
                "modifiers": {"type": "object"},
            }, "required": ["field_name", "position"]}},
        },
        required_inputs=["fields"],
        output_schema={
            "view_id": {"type": "integer"},
            "view_name": {"type": "string"},
            "view_url": {"type": "string"},
            "fields_added": {"type": "array", "items": {"type": "string"}},
        },
    )
    def _ai_add_field_to_view(self, fields=None, view_id=None, view_type=None, model=None, **kw):
        if not view_id and not view_type:
            view_type = "form"
        if not view_id and model:
            self = self.with_context(default_model=model)
        base_view = self._resolve_view(view_id, view_type)

        xpath_parts = []
        added = []

        for fdef in (fields or []):
            field_name = fdef["field_name"]
            position = fdef["position"]
            target = fdef.get("target", "")

            attrs = []
            if fdef.get("label"):
                attrs.append(f'string="{fdef["label"]}"')
            if fdef.get("widget"):
                attrs.append(f'widget="{fdef["widget"]}"')
            if fdef.get("placeholder"):
                attrs.append(f'placeholder="{fdef["placeholder"]}"')
            if fdef.get("nolabel"):
                attrs.append('nolabel="1"')
            for mod_attr in ("invisible", "readonly", "required"):
                if mod_attr in (fdef.get("modifiers") or {}):
                    attrs.append(f'{mod_attr}="{fdef["modifiers"][mod_attr]}"')
            attr_str = " " + " ".join(attrs) if attrs else ""
            field_xml = f'<field name="{field_name}"{attr_str}/>'

            if position == "before":
                if not target:
                    raise UserError(_("'target' is required for position 'before'."))
                xpath_parts.append(
                    f'<field name="{target}" position="before">{field_xml}</field>'
                )
            elif position == "after":
                if not target:
                    raise UserError(_("'target' is required for position 'after'."))
                xpath_parts.append(
                    f'<field name="{target}" position="after">{field_xml}</field>'
                )
            elif position == "inside":
                if not target:
                    raise UserError(_("'target' is required for position 'inside'."))
                xpath_parts.append(
                    f'<xpath expr="//{target}" position="inside">{field_xml}</xpath>'
                )
            elif position == "replace":
                if not target:
                    raise UserError(_("'target' is required for position 'replace'."))
                xpath_parts.append(
                    f'<field name="{target}" position="replace">{field_xml}</field>'
                )
            elif position == "attributes":
                if not target:
                    raise UserError(_("'target' is required for position 'attributes'."))
                xpath_parts.append(
                    f'<field name="{target}" position="attributes">{field_xml}</field>'
                )

            added.append(field_name)

        new_name = f"custom.{base_view.id}.fields"
        new_arch = (
            '<data><xpath expr="//sheet" position="attributes">\n'
            + "\n".join(xpath_parts)
            + "\n</xpath></data>"
            if xpath_parts else "<data/>"
        )

        new_view = self.env["ir.ui.view"].create({
            "name": new_name,
            "model": base_view.model,
            "inherit_id": base_view.id,
            "arch": new_arch,
            "priority": 100,
        })

        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        view_url = f"{base_url}/web#id={new_view.id}&model=ir.ui.view&view_type=form"

        return {
            "view_id": new_view.id,
            "view_name": new_view.name,
            "view_url": view_url,
            "fields_added": added,
        }

    # ------------------------------------------------------------------
    # TOOL 4: create_view
    # ------------------------------------------------------------------

    @aitool(
        input_schema={
            "prefix": {"type": "string"},
            "name": {"type": "string"},
            "model": {"type": "string"},
            "view_type": {"type": "string", "enum": [
                "form", "list", "kanban", "search", "graph",
                "pivot", "calendar", "gantt", "activity", "cohort",
            ]},
            "arch": {"type": "string", "description": "Full view XML arch"},
            "field_list": {"type": "array", "items": {"type": "string"},
                "description": "Field names for auto-generated arch"},
            "inherit_id": {"type": "string", "description": "XML ID to inherit"},
            "sequence": {"type": "integer", "description": "Priority"},
        },
        required_inputs=["prefix", "name", "model", "view_type"],
        output_schema={
            "view_id": {"type": "integer"},
            "view_name": {"type": "string"},
            "view_type": {"type": "string"},
        },
    )
    def _ai_create_view(self, prefix, name, model, view_type,
                         arch=None, field_list=None, inherit_id=None,
                         sequence=16, **kw):
        self._check_prefix(prefix)
        view_name = f"{prefix}.{name}" if prefix else name

        if inherit_id:
            inherit_view = self.env["ir.ui.view"].browse(
                self._parse_view_id(inherit_id)
            ) if inherit_id else None
        else:
            inherit_view = None

        if not arch:
            arch = self._auto_generate_arch(view_type, field_list or [])

        view = self.env["ir.ui.view"].create({
            "name": view_name,
            "model": model,
            "type": view_type,
            "arch": arch,
            "inherit_id": inherit_view.id if inherit_view else False,
            "priority": sequence,
        })

        return {
            "view_id": view.id,
            "view_name": view_name,
            "view_type": view_type,
        }

    def _auto_generate_arch(self, view_type, field_list):
        if view_type == "list":
            fields_xml = "\n".join(
                f'                    <field name="{f}"/>' for f in field_list
            )
            return f"""<list>
                    {fields_xml}
                </list>"""

        elif view_type == "form":
            fields_xml = "\n".join(
                f'                        <field name="{f}"/>' for f in field_list
            )
            return f"""<form>
                    <sheet>
                        <group>
                            {fields_xml}
                        </group>
                    </sheet>
                </form>"""

        elif view_type == "search":
            fields_xml = "\n".join(
                f'                <field name="{f}"/>' for f in field_list
            )
            return f"""<search>
                    {fields_xml}
                </search>"""

        elif view_type == "kanban":
            return """<kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>"""

        elif view_type == "graph":
            field = field_list[0] if field_list else "name"
            return f"""<graph type="bar">
                    <field name="{field}"/>
                </graph>"""

        elif view_type == "pivot":
            field = field_list[0] if field_list else "name"
            return f"""<pivot>
                    <field name="{field}" type="measure"/>
                </pivot>"""

        elif view_type == "calendar":
            return f"""<calendar date_start="date" color="color">
                    <field name="name"/>
                </calendar>"""

        elif view_type == "activity":
            return f"""<activity>
                    <field name="name"/>
                </activity>"""

        elif view_type == "cohort":
            return f"""<cohort date_start="date" date_stop="date">
                    <field name="name"/>
                </cohort>"""

        elif view_type == "gantt":
            return f"""<gantt date_start="date" date_stop="date">
                    <field name="name"/>
                </gantt>"""

        return f"<{view_type}><field name='name'/></{view_type}>"

    # ------------------------------------------------------------------
    # TOOL 5: create_server_action
    # ------------------------------------------------------------------

    @aitool(
        input_schema={
            "prefix": {"type": "string"},
            "name": {"type": "string"},
            "model_id": {"type": "string", "description": "Technical model name"},
            "action_type": {"type": "string", "enum": [
                "code", "object_create", "action", "client",
                "email", "followers", "next_activity",
            ]},
            "code": {"type": "string", "description": "Python code if type=code"},
            "state": {"type": "string"},
            "action_ref": {"type": "string"},
            "template_id": {"type": "string"},
            "usage": {"type": "string"},
        },
        required_inputs=["prefix", "name", "model_id", "action_type"],
        output_schema={
            "action_id": {"type": "integer"},
            "name": {"type": "string"},
        },
    )
    def _ai_create_server_action(self, prefix, name, model_id,
                                  action_type, **kw):
        self._check_prefix(prefix)
        ir_model = self.env["ir.model"].search(
            [("model", "=", model_id)], limit=1
        )
        if not ir_model:
            raise UserError(_("Model %s not found.") % model_id)

        vals = {
            "name": f"{prefix}.{name}",
            "model_id": ir_model.id,
            "state": action_type,
        }

        if action_type == "code" and kw.get("code"):
            vals["code"] = kw["code"]
        if kw.get("usage"):
            vals["usage"] = kw["usage"]

        action = self.env["ir.actions.server"].create(vals)
        return {"action_id": action.id, "name": action.name}

    # ------------------------------------------------------------------
    # TOOL 6: create_scheduled_action
    # ------------------------------------------------------------------

    @aitool(
        input_schema={
            "prefix": {"type": "string"},
            "name": {"type": "string"},
            "model_id": {"type": "string"},
            "code": {"type": "string"},
            "interval_number": {"type": "integer"},
            "interval_type": {"type": "string", "enum": [
                "minutes", "hours", "days", "weeks", "months",
            ]},
            "nextcall": {"type": "string", "description": "ISO datetime"},
            "priority": {"type": "integer"},
            "active": {"type": "boolean"},
        },
        required_inputs=["prefix", "name", "model_id", "code",
                         "interval_number", "interval_type"],
        output_schema={
            "cron_id": {"type": "integer"},
            "name": {"type": "string"},
        },
    )
    def _ai_create_scheduled_action(self, prefix, name, model_id, code,
                                     interval_number, interval_type, **kw):
        self._check_prefix(prefix)
        ir_model = self.env["ir.model"].search(
            [("model", "=", model_id)], limit=1
        )
        if not ir_model:
            raise UserError(_("Model %s not found.") % model_id)

        cron_name = f"{prefix}.{name}"
        existing = self.env["ir.cron"].search([("name", "=", cron_name)], limit=1)
        if existing:
            raise UserError(_("Scheduled action %s already exists.") % cron_name)

        from odoo import fields as odoo_fields

        nextcall = kw.get("nextcall") or odoo_fields.Datetime.now()

        vals = {
            "name": cron_name,
            "model_id": ir_model.id,
            "state": "code",
            "code": code,
            "interval_number": interval_number,
            "interval_type": interval_type,
            "nextcall": nextcall,
            "priority": kw.get("priority", 5),
            "active": kw.get("active", True),
        }

        cron = self.env["ir.cron"].create(vals)
        return {"cron_id": cron.id, "name": cron.name}

    # ------------------------------------------------------------------
    # TOOL 7: create_automated_action
    # ------------------------------------------------------------------

    @aitool(
        input_schema={
            "prefix": {"type": "string"},
            "name": {"type": "string"},
            "model_id": {"type": "string"},
            "trigger": {"type": "string", "enum": [
                "on_create", "on_write", "on_create_or_write",
                "on_unlink", "on_time",
            ]},
            "trigger_field_ids": {"type": "array", "items": {"type": "string"}},
            "filter_domain": {"type": "string"},
            "server_action_ids": {"type": "array", "items": {"type": "string"}},
            "interval_number": {"type": "integer"},
            "interval_type": {"type": "string"},
        },
        required_inputs=["prefix", "name", "model_id", "trigger"],
        output_schema={
            "automation_id": {"type": "integer"},
            "name": {"type": "string"},
            "model": {"type": "string"},
        },
    )
    def _ai_create_automated_action(self, prefix, name, model_id,
                                     trigger, **kw):
        self._check_prefix(prefix)
        ir_model = self.env["ir.model"].search(
            [("model", "=", model_id)], limit=1
        )
        if not ir_model:
            raise UserError(_("Model %s not found.") % model_id)

        vals = {
            "name": f"{prefix}.{name}",
            "model_id": ir_model.id,
            "trigger": trigger,
            "state": "code" if trigger != "on_time" else "time",
            "filter_pre_domain": kw.get("filter_domain", "[]"),
            "active": True,
        }

        if trigger == "on_time":
            vals["trg_date_field"] = kw.get("date_field", "create_date")
            vals["interval_number"] = kw.get("interval_number", 1)
            vals["interval_type"] = kw.get("interval_type", "days")

        if "base.automation" not in self.env.registry._models:
            raise UserError(_("Automated actions require 'base_automation' module to be installed."))
        automation = self.env["base.automation"].create(vals)

        return {
            "automation_id": automation.id,
            "name": automation.name,
            "model": model_id,
        }

    # ------------------------------------------------------------------
    # TOOL 8: create_access_rights
    # ------------------------------------------------------------------

    @aitool(
        input_schema={
            "model": {"type": "string", "description": "Technical model name"},
            "rules": {"type": "array", "items": {"type": "object", "properties": {
                "group_xml_id": {"type": "string",
                    "description": "e.g. base.group_user"},
                "perm_read": {"type": "boolean"},
                "perm_write": {"type": "boolean"},
                "perm_create": {"type": "boolean"},
                "perm_unlink": {"type": "boolean"},
            }, "required": ["group_xml_id"]}},
            "default_access": {"type": "string",
                "description": "Shorthand: base.group_user:read,write"},
        },
        required_inputs=["model"],
        output_schema={
            "model": {"type": "string"},
            "rules_created": {"type": "integer"},
        },
    )
    def _ai_create_access_rights(self, model, rules=None,
                                  default_access=None, **kw):
        ir_model = self.env["ir.model"].search(
            [("model", "=", model)], limit=1
        )
        if not ir_model:
            raise UserError(_("Model %s not found.") % model)

        resolved_rules = []

        if default_access:
            for part in default_access.split(";"):
                part = part.strip()
                if ":" in part:
                    group_ref, perms_raw = part.split(":", 1)
                    perm_list = [p.strip() for p in perms_raw.split(",")]
                    resolved_rules.append({
                        "group_xml_id": group_ref,
                        "perm_read": "read" in perm_list or "all" in perm_list,
                        "perm_write": "write" in perm_list or "all" in perm_list,
                        "perm_create": "create" in perm_list or "all" in perm_list,
                        "perm_unlink": "unlink" in perm_list or "all" in perm_list,
                    })

        if rules:
            resolved_rules.extend(rules)

        created = 0
        for rule in resolved_rules:
            group = self.env.ref(rule["group_xml_id"], raise_if_not_found=False)
            if not group:
                raise UserError(_("Group %s not found.") % rule["group_xml_id"])

            self.env["ir.model.access"].create({
                "name": f"{model}_{group.name}",
                "model_id": ir_model.id,
                "group_id": group.id,
                "perm_read": rule.get("perm_read", False),
                "perm_write": rule.get("perm_write", False),
                "perm_create": rule.get("perm_create", False),
                "perm_unlink": rule.get("perm_unlink", False),
            })
            created += 1

        return {"model": model, "rules_created": created}

    # ------------------------------------------------------------------
    # TOOL 9: export_customizations
    # ------------------------------------------------------------------

    @aitool(
        input_schema={
            "prefix": {"type": "string"},
        },
        required_inputs=["prefix"],
        output_schema={
            "download_url": {"type": "string"},
            "module_name": {"type": "string"},
            "models_count": {"type": "integer"},
            "views_count": {"type": "integer"},
            "actions_count": {"type": "integer"},
        },
    )
    def _ai_export_customizations(self, prefix, **kw):
        self._check_prefix(prefix)
        generator = CustomExportGenerator(self.env)
        result = generator.generate(prefix)

        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        download_url = (
            f"{base_url}/ai_custom_dev/export/{prefix}/download/{result['attachment_id']}"
        )

        return {
            "download_url": download_url,
            "module_name": prefix,
            "models_count": result["models_count"],
            "views_count": result["views_count"],
            "actions_count": result["actions_count"],
        }

    # ------------------------------------------------------------------
    # TOOL 11: create_or_update_translation
    # ------------------------------------------------------------------

    @aitool(
        input_schema={
            "model": {"type": "string", "description": "Model name (e.g. ir.model.fields)"},
            "record_id": {"type": "integer", "description": "Record ID to translate"},
            "field_name": {"type": "string", "description": "Field to translate (e.g. field_description, name)"},
            "language": {"type": "string", "description": "Language code (e.g. es_ES, fr_FR)"},
            "value": {"type": "string", "description": "Translated value"},
            "source_value": {"type": "string", "description": "Original English value (optional)"},
        },
        required_inputs=["model", "record_id", "field_name", "language", "value"],
        output_schema={
            "status": {"type": "string"},
            "translation_id": {"type": "integer"},
            "details": {"type": "string"},
        },
    )
    def _ai_create_or_update_translation(self, model, record_id, field_name,
                                          language, value, source_value=None, **kw):
        record = self.env[model].browse(record_id)
        if not record.exists():
            raise UserError(_("Record not found: %s %s") % (model, record_id))

        if not source_value:
            source_value = record[field_name]
            if isinstance(source_value, dict):
                source_value = source_value.get("en_US", "")

        existing = self.env["ir.translation"].search([
            ("name", "=", f"{model},{field_name}"),
            ("res_id", "=", record_id),
            ("lang", "=", language),
        ], limit=1)

        if existing:
            existing.write({
                "value": value,
                "src": source_value,
            })
            return {
                "status": "updated",
                "translation_id": existing.id,
                "details": f"Translation updated for {model} #{record_id} ({field_name}) to {language}",
            }

        translation = self.env["ir.translation"].create({
            "name": f"{model},{field_name}",
            "res_id": record_id,
            "lang": language,
            "type": "model",
            "src": source_value,
            "value": value,
            "state": "translated",
        })

        return {
            "status": "created",
            "translation_id": translation.id,
            "details": f"Translation created for {model} #{record_id} ({field_name}) to {language}",
        }

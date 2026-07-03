import base64
import io
import logging
import re
import zipfile
from datetime import datetime
from collections import defaultdict

from odoo import _, fields as odoo_fields

_logger = logging.getLogger(__name__)

PY_INHERIT_TPL = '''# Copyright {year} SDi
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class {class_name}(models.Model):
    _inherit = "{model_name}"

{fields}
'''


class CustomExportGenerator:
    def __init__(self, env):
        self.env = env

    def generate(self, prefix):
        custom_fields = self._collect_custom_fields(prefix)
        custom_models = self._collect_models(prefix)
        inherit_views = self._collect_inherit_views(prefix, custom_fields)
        actions_data = self._collect_actions(prefix)
        security_data = self._collect_security(prefix, custom_models)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            self._write_manifest(
                zf, prefix, custom_fields, custom_models,
                inherit_views, actions_data,
            )
            self._write_init(zf, prefix, custom_fields)
            self._write_models_py(zf, prefix, custom_models)
            self._write_inherit_py(zf, prefix, custom_fields)
            self._write_inherit_views(zf, prefix, inherit_views)
            self._write_security(zf, prefix, security_data, custom_models)
            self._write_actions(zf, prefix, actions_data, custom_models)
            self._write_translations(zf, prefix, custom_fields)

        buffer.seek(0)
        attachment = self.env["ir.attachment"].create({
            "name": f"{prefix}_module.zip",
            "datas": base64.b64encode(buffer.read()),
            "mimetype": "application/zip",
        })

        return {
            "attachment_id": attachment.id,
            "models_count": len(custom_models),
            "views_count": len(inherit_views),
            "actions_count": sum(len(v) for v in actions_data.values()),
        }

    def _collect_custom_fields(self, prefix):
        grouped = defaultdict(list)
        fields_rec = self.env["ir.model.fields"].search([
            ("name", "=like", f"x_{prefix}%"),
        ])
        for f in fields_rec:
            clean_name = self._strip_prefix(f.name, prefix)
            label = f.field_description
            if isinstance(label, dict):
                label = label.get("en_US", str(label))
            grouped[f.model].append({
                "record": f,
                "clean_name": clean_name,
                "label": label,
            })
        return grouped

    def _strip_prefix(self, name, prefix):
        result = name
        result = re.sub(rf"^x_{prefix}_", "", result)
        return result

    def _collect_models(self, prefix):
        result = []
        for rec in self.env["ir.model"].search([
            ("model", "=like", f"x_{prefix}.%"),
        ]):
            fields_rec = self.env["ir.model.fields"].search([
                ("model_id", "=", rec.id),
                ("name", "not in", ("id", "display_name", "create_uid",
                                     "create_date", "write_uid", "write_date",
                                     "__last_update")),
            ])
            result.append({
                "record": rec,
                "fields": fields_rec,
            })
        return result

    def _collect_inherit_views(self, prefix, custom_fields):
        views = self.env["ir.ui.view"].search([
            ("name", "=like", f"{prefix}.%"),
            ("inherit_id", "!=", False),
        ])
        if not views:
            views = self.env["ir.ui.view"].search([
                ("name", "=like", "custom.%"),
                ("inherit_id", "!=", False),
            ])
        result = []
        for v in views:
            arch = v.arch_db
            for model_name, fields in custom_fields.items():
                for f in fields:
                    old_name = f["record"].name
                    clean = f["clean_name"]
                    arch = arch.replace(old_name, clean)
            result.append({
                "record": v,
                "arch": arch,
            })
        return result

    def _collect_actions(self, prefix):
        try:
            automation_model = self.env["base.automation"]
        except KeyError:
            automation_model = None
        return {
            "server": self.env["ir.actions.server"].search([
                ("name", "=like", f"{prefix}.%"),
            ]),
            "cron": self.env["ir.cron"].search([
                ("name", "=like", f"{prefix}.%"),
            ]),
            "automation": automation_model.search([
                ("name", "=like", f"{prefix}.%"),
            ]) if automation_model else self.env["ir.model"].browse(),
        }

    def _collect_security(self, prefix, custom_models):
        model_ids = [m["record"].id for m in custom_models]
        return self.env["ir.model.access"].search([
            ("model_id", "in", model_ids),
        ])

    def _write_manifest(self, zf, prefix, custom_fields, custom_models,
                        inherit_views, actions_data):
        depends = ["mail", "base"]
        data_files = []

        models_with_fields = set()
        if custom_fields:
            for model_name in custom_fields:
                models_with_fields.add(
                    model_name.replace(".", "_") if "." in model_name
                    else model_name
                )
            data_files.append("data/custom_fields.xml")

        if inherit_views:
            data_files.append("data/inherit_views.xml")

        if custom_models:
            data_files.append("security/ir.model.access.csv")

        if actions_data["server"]:
            data_files.append("data/server_actions.xml")
        if actions_data["cron"]:
            data_files.append("data/scheduled_actions.xml")
        if actions_data["automation"]:
            data_files.append("data/automated_actions.xml")

        manifest = (
            f'{{"name": "{prefix}",\n'
            f' "version": "18.0.1.0.0",\n'
            f' "license": "AGPL-3",\n'
            f' "depends": {depends!r},\n'
            f' "data": {data_files!r},\n'
            f' "installable": True,\n'
            f' "application": True,\n'
            f' "author": "AI Custom Development",\n'
            f'}}\n'
        )
        zf.writestr(f"{prefix}/__manifest__.py", manifest)

    def _write_init(self, zf, prefix, custom_fields):
        lines = ["from . import models"]
        if custom_fields:
            lines.append("from . import inherit_models")
        zf.writestr(f"{prefix}/__init__.py", "\n".join(lines) + "\n")
        zf.writestr(f"{prefix}/models/__init__.py", "")

    def _write_models_py(self, zf, prefix, custom_models):
        if not custom_models:
            return
        for m in custom_models:
            rec = m["record"]
            name = rec.model.split(".")[-1]
            class_name = "".join(
                part.capitalize() for part in f"{prefix}_{name}".split("_")
            )
            field_lines = []
            for f in m["fields"]:
                py_type = self._field_type_to_python(f.ttype)
                args = [f"string={f.field_description!r}"]
                if f.required:
                    args.append("required=True")
                if f.index:
                    args.append("index=True")
                if f.readonly:
                    args.append("readonly=True")
                if f.ttype == "selection" and f.selection:
                    sel = [
                        f"('{k}', '{v}')"
                        for k, v in self._parse_sel(f.selection)
                    ]
                    args.append(f"selection=[{', '.join(sel)}]")
                if f.relation:
                    args.append(f"comodel_name='{f.relation}'")
                if f.ttype == "monetary":
                    args.append("currency_field='currency_id'")
                if f.help:
                    args.append(f"help={f.help!r}")
                if f.tracking:
                    args.append("tracking=True")
                field_lines.append(
                    f"    {f.name} = fields.{py_type}({', '.join(args)})"
                )
        py_content = PY_INHERIT_TPL.format(
            year=datetime.now().year,
            class_name=class_name,
            model_name=rec.model,
            fields="\n".join(field_lines) if field_lines else "    pass",
        )
        zf.writestr(f"{prefix}/models/{name}.py", py_content)

        init_lines = ["from . import " + m["record"].model.split(".")[-1]
                      for m in custom_models]
        zf.writestr(
            f"{prefix}/models/__init__.py",
            "\n".join(init_lines) + "\n",
        )

    def _write_inherit_py(self, zf, prefix, custom_fields):
        if not custom_fields:
            return
        init_lines = []
        for model_name, fields in custom_fields.items():
            if model_name.startswith("x_"):
                continue
            module_name = model_name.replace(".", "_")
            class_name = "".join(
                part.capitalize() for part in f"{prefix}_{model_name}".replace(".", "_").split("_")
            )

            field_lines = []
            for f in fields:
                rec = f["record"]
                py_type = self._field_type_to_python(rec.ttype)
                clean = f["clean_name"]
                label = f["label"]
                args = [f"string={label!r}"]
                if rec.required:
                    args.append("required=True")
                if rec.index:
                    args.append("index=True")
                if rec.readonly:
                    args.append("readonly=True")
                if rec.ttype == "selection" and rec.selection:
                    sel = [
                        f"('{k}', '{v}')"
                        for k, v in self._parse_sel(rec.selection)
                    ]
                    args.append(f"selection=[{', '.join(sel)}]")
                if rec.relation:
                    args.append(f"comodel_name='{rec.relation}'")
                if rec.ttype == "monetary":
                    args.append("currency_field='currency_id'")
                if rec.help:
                    args.append(f"help={rec.help!r}")
                if rec.tracking:
                    args.append("tracking=True")
                field_lines.append(
                    f"    {clean} = fields.{py_type}({', '.join(args)})"
                )

            py_content = PY_INHERIT_TPL.format(
                year=datetime.now().year,
                class_name=class_name,
                model_name=model_name,
                fields="\n".join(field_lines),
            )

            filename = f"{prefix}/inherit_models/{module_name}.py"
            zf.writestr(filename, py_content)
            init_lines.append(f"from . import {module_name}")

        zf.writestr(
            f"{prefix}/inherit_models/__init__.py",
            "\n".join(init_lines) + "\n",
        )

    def _write_inherit_views(self, zf, prefix, inherit_views):
        if not inherit_views:
            return
        xml_parts = ['<?xml version="1.0" encoding="utf-8"?>', '<odoo>\n']
        for v in inherit_views:
            view = v["record"]
            view_ref = view.name.replace(".", "_")
            xml_parts.append(
                f'  <record id="{view_ref}" model="ir.ui.view">\n'
                f'    <field name="name">{view.name}</field>\n'
                f'    <field name="model">{view.model}</field>\n'
                f'    <field name="inherit_id" ref="{view.model.replace(".", "_")}_form"/>\n'
                f'    <field name="arch" type="xml">\n'
                f'{v["arch"]}\n'
                f'    </field>\n'
                f'  </record>\n'
            )
        xml_parts.append('</odoo>\n')
        zf.writestr(f"{prefix}/data/inherit_views.xml", "\n".join(xml_parts))

    def _write_security(self, zf, prefix, security_data, custom_models):
        lines = [
            "id,name,model_id:id,group_id:id,"
            "perm_read,perm_write,perm_create,perm_unlink"
        ]
        for ac in security_data:
            group_id = (
                f"base.group_{ac.group_id.name.lower().replace(' ', '_')}"
                if ac.group_id
                else ""
            )
            model_ref = f"model_{ac.model_id.model.replace('.', '_')}"
            lines.append(
                f"{ac.id},{ac.name},{model_ref},"
                f"{group_id if ac.group_id else ''},"
                f"{ac.perm_read},{ac.perm_write},"
                f"{ac.perm_create},{ac.perm_unlink}"
            )
        refs_xml = '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n'
        for m in custom_models:
            ref = f"model_{m['record'].model.replace('.', '_')}"
            refs_xml += (
                f'  <record id="{ref}" model="ir.model">\n'
                f'    <field name="name">{m["record"].name}</field>\n'
                f'    <field name="model">{m["record"].model}</field>\n'
                f'  </record>\n'
            )
        refs_xml += "</odoo>\n"
        if security_data or custom_models:
            zf.writestr(
                f"{prefix}/security/ir.model.access.csv",
                "\n".join(lines) + "\n",
            )
            zf.writestr(f"{prefix}/security/ir_model_data.xml", refs_xml)

    def _write_actions(self, zf, prefix, actions_data, custom_models):
        if actions_data["server"]:
            content = '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n'
            for action in actions_data["server"]:
                content += (
                    f'  <record id="{action.name}" model="ir.actions.server">\n'
                    f'    <field name="name">{action.name}</field>\n'
                    f'    <field name="model_id"'
                    f' ref="model_{action.model_id.model.replace(".", "_")}"/>\n'
                    f'    <field name="state">{action.state}</field>\n'
                    f'  </record>\n'
                )
            content += "</odoo>\n"
            zf.writestr(f"{prefix}/data/server_actions.xml", content)

        if actions_data["cron"]:
            content = '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n'
            for cron in actions_data["cron"]:
                content += (
                    f'  <record id="{cron.name}" model="ir.cron">\n'
                    f'    <field name="name">{cron.name}</field>\n'
                    f'    <field name="model_id">{cron.model_id}</field>\n'
                    f'    <field name="state">code</field>\n'
                    f'    <field name="code">{cron.code}</field>\n'
                    f'    <field name="interval_number">{cron.interval_number}</field>\n'
                    f'    <field name="interval_type">{cron.interval_type}</field>\n'
                    f'  </record>\n'
                )
            content += "</odoo>\n"
            zf.writestr(f"{prefix}/data/scheduled_actions.xml", content)

        if actions_data["automation"]:
            content = '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n'
            for auto in actions_data["automation"]:
                content += (
                    f'  <record id="{auto.name}" model="base.automation">\n'
                    f'    <field name="name">{auto.name}</field>\n'
                    f'    <field name="model_id"'
                    f' ref="model_{auto.model_id.model.replace(".", "_")}"/>\n'
                    f'    <field name="trigger">{auto.trigger}</field>\n'
                    f'  </record>\n'
                )
            content += "</odoo>\n"
            zf.writestr(f"{prefix}/data/automated_actions.xml", content)

    def _write_translations(self, zf, prefix, custom_fields):
        if not custom_fields:
            return
        try:
            trans_model = self.env["ir.translation"]
        except KeyError:
            return
        po_lines = [
            f"# Translation of {prefix} module.",
            'msgid ""',
            'msgstr ""',
            '"Project-Id-Version: Odoo 18.0\\n"',
            '"POT-Creation-Date: 2026-01-01 00:00+0000\\n"',
            '"PO-Revision-Date: 2026-01-01 00:00+0000\\n"',
            '"Last-Translator: AI Custom Development\\n"',
            '"Language-Team: Spanish\\n"',
            '"MIME-Version: 1.0\\n"',
            '"Content-Type: text/plain; charset=UTF-8\\n"',
            '"Content-Transfer-Encoding: 8bit\\n"',
            '"Plural-Forms: nplurals=2; plural=(n != 1);\\n"',
            '"Language: es_ES\\n"',
            "",
        ]
        for model_name, fields in custom_fields.items():
            for f in fields:
                rec = f["record"]
                label = f["label"]
                try:
                    translations = self.env["ir.translation"].search([
                        ("name", "=", f"ir.model.fields,field_description"),
                        ("res_id", "=", rec.id),
                        ("lang", "=", "es_ES"),
                    ], limit=1)
                except KeyError:
                    continue
                if translations:
                    po_lines.append(f"#. module: {prefix}")
                    po_lines.append(f"#: model:ir.model.fields,name:{rec.name}")
                    po_lines.append(f'msgid "{label}"')
                    po_lines.append(f'msgstr "{translations.value}"')
                    po_lines.append("")

        zf.writestr(f"{prefix}/i18n/es_ES.po", "\n".join(po_lines))

    def _field_type_to_python(self, ttype):
        mapping = {
            "char": "Char",
            "text": "Text",
            "html": "Html",
            "integer": "Integer",
            "float": "Float",
            "boolean": "Boolean",
            "date": "Date",
            "datetime": "Datetime",
            "binary": "Binary",
            "selection": "Selection",
            "many2one": "Many2one",
            "one2many": "One2many",
            "many2many": "Many2many",
            "monetary": "Monetary",
        }
        return mapping.get(ttype, "Char")

    def _parse_sel(self, selection_str):
        result = []
        for line in selection_str.split("\n"):
            line = line.strip()
            if ":" in line:
                k, v = line.split(":", 1)
                result.append((k.strip(), v.strip()))
        return result

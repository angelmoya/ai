# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from psycopg2 import sql

_logger = logging.getLogger(__name__)

BACKUP_TABLE = "_ai_skill_ai_connection_rel_backup"
REL_TABLE = "ai_skill_ai_connection_rel"


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        "SELECT table_name FROM information_schema.tables " "WHERE table_name = %s",
        (REL_TABLE,),
    )
    if not cr.fetchone():
        _logger.info("Relation table %s does not exist, nothing to backup", REL_TABLE)
        return

    cr.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(BACKUP_TABLE)))
    cr.execute(
        sql.SQL("CREATE TABLE {} AS SELECT * FROM {}").format(
            sql.Identifier(BACKUP_TABLE), sql.Identifier(REL_TABLE)
        )
    )
    cr.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(BACKUP_TABLE)))
    count = cr.fetchone()[0]
    _logger.info("Backed up %d rows from %s", count, REL_TABLE)

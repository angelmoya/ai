# Copyright 2026 SDi - Ángel Moya <amoya@sdi.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

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

    cr.execute("DROP TABLE IF EXISTS %s" % BACKUP_TABLE)
    cr.execute("CREATE TABLE %s AS SELECT * FROM %s" % (BACKUP_TABLE, REL_TABLE))
    cr.execute("SELECT COUNT(*) FROM %s" % BACKUP_TABLE)
    count = cr.fetchone()[0]
    _logger.info("Backed up %d rows from %s", count, REL_TABLE)

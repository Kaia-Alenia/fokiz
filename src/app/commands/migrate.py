from __future__ import annotations
import logging
from ..i18n import _
from .. import db, ui
from ..integrity import check_contract_integrity, IntegrityStatus, migrate_contract_to_v2

log = logging.getLogger(__name__)

def cmd_migrate() -> int:
    """fokiz migrate — Migrates V1 contracts to V2."""
    if not db.db_exists():
        ui.print_error(_("error.not_initialized"))
        return 1

    tasks = db.get_all_tasks()
    migrated_count = 0

    for task in tasks:
        phases = db.get_phases(task["id"])
        status = check_contract_integrity(task, phases)

        if status == IntegrityStatus.MIGRATION_REQUIRED:
            new_hash = migrate_contract_to_v2(task, phases)
            db.finalize_task_hmac(task["id"], new_hash)
            migrated_count += 1
            ui.print_info(f"Task #{task['id']} migrated to HMAC V2.")
        elif status == IntegrityStatus.TAMPERED:
            ui.print_tampered_warning(task["id"])

    if migrated_count == 0:
        ui.print_info(_("migrate.no_tasks"))
    else:
        ui.print_success(_("migrate.success", count=migrated_count))
    return 0

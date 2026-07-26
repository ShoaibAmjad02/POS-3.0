import logging
from django.core.management.base import BaseCommand
from megaone.users.backup_utils import run_backup, should_run_auto_backup

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Creates a database backup if 24 hours have passed since the last backup"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force backup even if 24 hours have not passed",
        )
        parser.add_argument(
            "--no-checks",
            action="store_true",
            help="Skip auto-backup enabled check",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        no_checks = options.get("no_checks", False)

        if not force and not no_checks:
            if not should_run_auto_backup():
                self.stdout.write(self.style.NOTICE("Skipping backup: 24 hours have not passed yet"))
                return

        self.stdout.write(self.style.NOTICE("Starting database backup..."))
        result = run_backup()

        if result["success"]:
            size_kb = result["size"] / 1024
            self.stdout.write(self.style.SUCCESS(f"Backup completed successfully ({size_kb:.1f} KB)"))
        else:
            self.stdout.write(self.style.ERROR(f"Backup failed: {result['error']}"))

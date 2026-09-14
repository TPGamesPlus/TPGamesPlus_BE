import logging
import os
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)

# Management commands that must never trigger a DB-touching import on app load.
_SKIP_COMMANDS = {
    "makemigrations", "migrate", "test", "shell", "shell_plus", "check",
    "collectstatic", "createsuperuser", "startapp", "startproject",
}


class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalog'

    def ready(self):
        if "pytest" in sys.modules:  # pytest-django never goes through manage.py's argv
            return

        argv = sys.argv
        if len(argv) > 1 and argv[1] in _SKIP_COMMANDS:
            return

        # runserver's autoreloader spawns a child (RUN_MAIN=true) that should do the real work;
        # skip the parent watcher process so the import doesn't run twice.
        is_runserver = len(argv) > 1 and argv[1] == "runserver"
        if is_runserver and "--noreload" not in argv and os.environ.get("RUN_MAIN") != "true":
            return

        try:
            from django.core.management import call_command
            call_command("import_products")
        except Exception:
            logger.warning("Startup CSV import skipped (DB likely not migrated yet)", exc_info=True)

import time

from django.core.management.base import BaseCommand
from django.db import OperationalError, connections


class Command(BaseCommand):
    help = "Wait until the default database accepts connections."

    def handle(self, *args, **options):
        self.stdout.write("Waiting for database...")
        for _ in range(30):
            try:
                connections["default"].cursor()
                self.stdout.write(self.style.SUCCESS("Database is available."))
                return
            except OperationalError:
                time.sleep(1)
        raise OperationalError("Database is not available after 30 seconds.")

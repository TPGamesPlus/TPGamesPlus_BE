import csv
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Product
from catalog.store import load_products


class Command(BaseCommand):
    help = "Import products from a CSV file (columns: id,title,description,price,location)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(settings.BASE_DIR / "data" / "items.csv"),
            help="Path to the CSV file to import (default: data/items.csv)",
        )

    def handle(self, *args, **options):
        path = options["file"]
        created = 0
        updated = 0

        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                with transaction.atomic():
                    for row in reader:
                        try:
                            external_id = int(row["id"])
                            price = Decimal(row["price"])
                        except (KeyError, ValueError, InvalidOperation) as exc:
                            raise CommandError(f"Invalid row {row!r}: {exc}") from exc

                        _, was_created = Product.objects.update_or_create(
                            external_id=external_id,
                            defaults={
                                "title": row["title"],
                                "description": row.get("description", ""),
                                "price": price,
                                "location": row["location"],
                            },
                        )
                        created += was_created
                        updated += not was_created
        except FileNotFoundError as exc:
            raise CommandError(f"CSV file not found: {path}") from exc

        load_products()  # keep the in-memory map in sync with what was just imported
        self.stdout.write(
            self.style.SUCCESS(f"Import complete: {created} created, {updated} updated (source: {path})")
        )

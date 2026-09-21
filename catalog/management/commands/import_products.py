import csv
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Product

REQUIRED_COLUMNS = ("id", "title", "description", "price", "location")


def _validate_header(header):
    names = [column.strip() for column in header]
    expected = list(REQUIRED_COLUMNS)
    if len(names) != len(expected):
        raise CommandError(
            f"CSV header has {len(names)} column(s), expected {len(expected)}: {', '.join(expected)}"
        )
    if names != expected:
        raise CommandError(
            f"CSV header {names} does not match required columns {expected}"
        )
    return names


def _row_issues(line_number, row, header):
    expected_count = len(header)
    found_count = len(row)
    if found_count != expected_count:
        if found_count < expected_count:
            missing = header[found_count:]
            return [
                (
                    f"Row {line_number}: expected {expected_count} columns, found {found_count}; "
                    f"missing values for: {', '.join(missing)}"
                )
            ]
        return [
            (
                f"Row {line_number}: expected {expected_count} columns, found {found_count}; "
                "extra fields present"
            )
        ]

    missing = [header[index] for index, value in enumerate(row) if not (value or "").strip()]
    if missing:
        return [f"Row {line_number}: missing values for columns: {', '.join(missing)}"]
    return []


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
            with open(path, newline="", encoding="utf-8") as handle:
                reader = csv.reader(handle)
                try:
                    header = next(reader)
                except StopIteration as exc:
                    raise CommandError("CSV file is empty.") from exc

                header = _validate_header(header)
                errors = []
                valid_rows = []
                for line_number, row in enumerate(reader, start=2):
                    issues = _row_issues(line_number, row, header)
                    if issues:
                        errors.extend(issues)
                        continue
                    valid_rows.append(
                        {name: value.strip() for name, value in zip(header, row, strict=True)}
                    )

                if errors:
                    for message in errors:
                        self.stderr.write(self.style.ERROR(message))
                    raise CommandError(
                        f"CSV validation failed: {len(errors)} row(s) have missing values. Import aborted."
                    )

                with transaction.atomic():
                    for row in valid_rows:
                        try:
                            external_id = int(row["id"])
                            price = Decimal(row["price"])
                        except (ValueError, InvalidOperation) as exc:
                            raise CommandError(f"Invalid row {row!r}: {exc}") from exc

                        _, was_created = Product.objects.update_or_create(
                            external_id=external_id,
                            defaults={
                                "title": row["title"],
                                "description": row["description"],
                                "price": price,
                                "location": row["location"],
                            },
                        )
                        created += was_created
                        updated += not was_created
        except FileNotFoundError as exc:
            raise CommandError(f"CSV file not found: {path}") from exc

        self.stdout.write(
            self.style.SUCCESS(f"Import complete: {created} created, {updated} updated (source: {path})")
        )

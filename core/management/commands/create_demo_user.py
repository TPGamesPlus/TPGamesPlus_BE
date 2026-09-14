from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed (or update) a demo user account for local development/grading."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]

        user, created = User.objects.get_or_create(username=username)
        user.set_password(options["password"])
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} demo user '{username}'"))

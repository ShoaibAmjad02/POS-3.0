from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

User = get_user_model()


class Command(BaseCommand):
    help = "Create the Software Owner account (highest system authority). Only one can exist."

    def add_arguments(self, parser):
        parser.add_argument("--email", help="Email address for the Software Owner")
        parser.add_argument("--name", help="Full name for the Software Owner")
        parser.add_argument("--password", help="Password for the Software Owner")
        parser.add_argument("--force", action="store_true", help="Allow creating a new Software Owner even if one already exists (deactivates the old one)")

    def handle(self, *args, **options):
        existing = User.objects.filter(is_software_owner=True).first()
        if existing:
            if not options.get("force"):
                self.stderr.write(self.style.ERROR(
                    "A Software Owner account already exists (email: %s). "
                    "Use --force to create a new one (the existing one will be deactivated)."
                    % existing.email
                ))
                return
            self.stdout.write(self.style.WARNING(
                "Deactivating existing Software Owner: %s" % existing.email
            ))
            existing.is_software_owner = False
            existing.is_active = False
            existing.save()

        email = options.get("email")
        name = options.get("name")
        password = options.get("password")

        if not email:
            email = input("Email address: ").strip()
        if not name:
            name = input("Full name: ").strip()
        if not password:
            import getpass
            password = getpass.getpass("Password: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                raise CommandError("Passwords do not match.")

        if not email or not name or not password:
            raise CommandError("Email, name, and password are required.")

        user = User.objects.create_user(
            email=email,
            name=name,
            password=password,
            is_software_owner=True,
            is_staff=True,
            is_superuser=False,
            is_active=True,
        )

        self.stdout.write(self.style.SUCCESS(
            "Software Owner account created successfully!\n"
            "  Email: %s\n"
            "  Name: %s\n"
            "  Login at the normal login page." % (user.email, user.name)
        ))

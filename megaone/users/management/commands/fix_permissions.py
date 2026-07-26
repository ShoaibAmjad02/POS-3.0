from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Q
from megaone.users.models import OperatorPermission

User = get_user_model()


class Command(BaseCommand):
    help = "Create missing OperatorPermission records for all staff/operator users"

    def handle(self, *args, **options):
        users = User.objects.filter(
            Q(is_operator=True) | Q(is_staff=True)
        ).exclude(is_software_owner=True)

        fixed = 0
        for u in users:
            try:
                _ = u.operator_permissions
            except Exception:
                perms = OperatorPermission.objects.create(user=u)
                if u.is_staff:
                    all_perms = [f.name for f in OperatorPermission._meta.get_fields() if f.name.startswith('can_')]
                    for pname in all_perms:
                        setattr(perms, pname, True)
                    perms.save()
                fixed += 1
                self.stdout.write(self.style.SUCCESS(f"  Created permissions for {u.email}"))

        self.stdout.write(self.style.SUCCESS(f"\nDone! {fixed} missing permission records created."))

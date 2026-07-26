from django.db import migrations


def populate_cash_permissions(apps, schema_editor):
    OperatorPermission = apps.get_model('users', 'OperatorPermission')
    User = apps.get_model('users', 'User')
    staff_user_ids = User.objects.filter(
        is_staff=True, is_software_owner=False
    ).values_list('pk', flat=True)
    cash_fields = [
        f.name for f in OperatorPermission._meta.get_fields()
        if f.name.startswith('cash_') and f.get_internal_type() == 'BooleanField'
    ]
    updated = 0
    for perm in OperatorPermission.objects.filter(user_id__in=staff_user_ids):
        changed = False
        for field in cash_fields:
            if not getattr(perm, field, False):
                setattr(perm, field, True)
                changed = True
        if changed:
            perm.save()
            updated += 1


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0033_operatorpermission_cash_audit_logs_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_cash_permissions, reverse_code=migrations.RunPython.noop),
    ]

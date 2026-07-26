from django.db import migrations


def _get_cash_boolean_field_names(model):
    names = []
    for f in model._meta.get_fields():
        if not f.name.startswith('cash_'):
            continue
        if not hasattr(f, 'get_internal_type'):
            continue
        if f.get_internal_type() != 'BooleanField':
            continue
        names.append(f.name)
    return names


def ensure_staff_cash_permissions(apps, schema_editor):
    OperatorPermission = apps.get_model('users', 'OperatorPermission')
    User = apps.get_model('users', 'User')
    cash_fields = _get_cash_boolean_field_names(OperatorPermission)
    staff_ids = set(
        User.objects.filter(is_staff=True, is_software_owner=False)
        .values_list('pk', flat=True)
    )
    updated = 0
    for perm in OperatorPermission.objects.filter(user_id__in=staff_ids):
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
        ('users', '0037_ensure_cash_handling_in_enabled_modules'),
    ]

    operations = [
        migrations.RunPython(ensure_staff_cash_permissions, reverse_code=migrations.RunPython.noop),
    ]

import json

from django.db import migrations


def ensure_cash_handling_module(apps, schema_editor):
    SystemSetting = apps.get_model('users', 'SystemSetting')
    for s in SystemSetting.objects.filter(pk=1):
        modules = list(s.enabled_modules or [])
        if 'cash_handling' not in modules:
            modules.append('cash_handling')
            s.enabled_modules = modules
            s.save()


def reverse_module(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0036_add_cash_session_perms'),
    ]

    operations = [
        migrations.RunPython(ensure_cash_handling_module, reverse_module),
    ]

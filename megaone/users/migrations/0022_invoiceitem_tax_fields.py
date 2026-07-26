from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0021_add_can_access_wholesale_permission'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoiceitem',
            name='tax_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='tax_percentage',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]

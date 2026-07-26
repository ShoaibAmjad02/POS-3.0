from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0022_invoiceitem_tax_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoiceitem',
            name='unit_cost_at_sale',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Product cost per unit at time of sale', max_digits=10),
        ),
        migrations.AddField(
            model_name='wholesaleinvoiceitem',
            name='unit_cost_at_sale',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Product cost per unit at time of sale', max_digits=10),
        ),
    ]

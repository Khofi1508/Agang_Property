from django.db import migrations, models


def mark_already_paid_properties_sold(apps, schema_editor):
    Property = apps.get_model('e_commerce', 'Property')
    PaymentOrder = apps.get_model('e_commerce', 'PaymentOrder')
    paid_property_ids = PaymentOrder.objects.filter(status='paid').values_list('properti_id', flat=True).distinct()
    Property.objects.filter(pk__in=paid_property_ids).update(status_penjualan='sold')


class Migration(migrations.Migration):

    dependencies = [
        ('e_commerce', '0016_midtrans_sandbox_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='status_penjualan',
            field=models.CharField(
                choices=[('available', 'Tersedia'), ('sold', 'Sold')],
                db_index=True,
                default='available',
                max_length=12,
                verbose_name='Status penjualan',
            ),
        ),
        migrations.RunPython(mark_already_paid_properties_sold, migrations.RunPython.noop),
    ]

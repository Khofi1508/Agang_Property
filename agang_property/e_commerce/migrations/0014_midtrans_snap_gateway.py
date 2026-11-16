# Switch the active payment flow from DOKU Checkout to Midtrans Snap.
import django.db.models.deletion
from django.db import migrations, models


def mark_legacy_doku_orders(apps, schema_editor):
    PaymentOrder = apps.get_model('e_commerce', 'PaymentOrder')
    PaymentOrder.objects.all().update(payment_gateway='doku_legacy')
    PaymentOrder.objects.filter(status='pending').update(status='expired')


class Migration(migrations.Migration):

    dependencies = [
        ('e_commerce', '0013_property_youtube_video_url_paymentorder_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='DokuNotificationEvent',
            new_name='PaymentNotificationEvent',
        ),
        migrations.RenameField(
            model_name='paymentnotificationevent',
            old_name='request_id',
            new_name='event_key',
        ),
        migrations.AlterField(
            model_name='paymentnotificationevent',
            name='payment',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='notifications',
                to='e_commerce.paymentorder',
            ),
        ),
        migrations.AlterModelOptions(
            name='paymentnotificationevent',
            options={
                'verbose_name': 'Notifikasi Pembayaran Gateway',
                'verbose_name_plural': 'Notifikasi Pembayaran Gateway',
            },
        ),
        migrations.RenameField(
            model_name='paymentorder',
            old_name='doku_checkout_url',
            new_name='payment_url',
        ),
        migrations.RenameField(
            model_name='paymentorder',
            old_name='doku_channel',
            new_name='payment_channel',
        ),
        migrations.RenameField(
            model_name='paymentorder',
            old_name='doku_payload',
            new_name='payment_payload',
        ),
        migrations.AlterField(
            model_name='paymentorder',
            name='metode_pembayaran',
            field=models.CharField(default='Midtrans Snap', max_length=50),
        ),
        migrations.AddField(
            model_name='paymentorder',
            name='payment_token',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='paymentorder',
            name='payment_transaction_id',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='paymentorder',
            name='payment_type',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='paymentorder',
            name='payment_gateway',
            field=models.CharField(
                choices=[('midtrans', 'Midtrans Sandbox'), ('doku_legacy', 'DOKU (transaksi lama)')],
                default='doku_legacy',
                max_length=20,
            ),
        ),
        migrations.RunPython(mark_legacy_doku_orders, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='paymentorder',
            name='payment_gateway',
            field=models.CharField(
                choices=[('midtrans', 'Midtrans Sandbox'), ('doku_legacy', 'DOKU (transaksi lama)')],
                default='midtrans',
                max_length=20,
            ),
        ),
    ]

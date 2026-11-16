from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('e_commerce', '0014_midtrans_snap_gateway'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentorder',
            name='metode_pembayaran',
            field=models.CharField(default='DOKU Checkout', max_length=50),
        ),
        migrations.AlterField(
            model_name='paymentorder',
            name='payment_gateway',
            field=models.CharField(
                choices=[
                    ('doku', 'DOKU Checkout Sandbox'),
                    ('midtrans', 'Midtrans Sandbox'),
                    ('doku_legacy', 'DOKU (transaksi lama)'),
                ],
                default='doku',
                max_length=20,
            ),
        ),
    ]

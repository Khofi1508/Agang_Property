from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('e_commerce', '0015_doku_checkout_sandbox'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentorder',
            name='metode_pembayaran',
            field=models.CharField(default='Midtrans Snap', max_length=50),
        ),
        migrations.AlterField(
            model_name='paymentorder',
            name='payment_gateway',
            field=models.CharField(
                choices=[
                    ('midtrans', 'Midtrans Sandbox'),
                    ('doku', 'DOKU Checkout Sandbox'),
                    ('doku_legacy', 'DOKU (transaksi lama)'),
                ],
                default='midtrans',
                max_length=20,
            ),
        ),
    ]

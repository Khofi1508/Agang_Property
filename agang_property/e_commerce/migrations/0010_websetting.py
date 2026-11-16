from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('e_commerce', '0009_heroslide'),
    ]

    operations = [
        migrations.CreateModel(
            name='WebSetting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nama_website', models.CharField(default='Agang Property', max_length=120)),
                ('tagline', models.CharField(blank=True, max_length=200)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='website/')),
                ('email_kontak', models.EmailField(blank=True, max_length=254)),
                ('telepon_kontak', models.CharField(blank=True, max_length=30)),
                ('whatsapp', models.CharField(blank=True, help_text='Gunakan format internasional, contoh: 628118900234.', max_length=30)),
                ('alamat', models.TextField(blank=True)),
                ('instagram_url', models.URLField(blank=True)),
                ('facebook_url', models.URLField(blank=True)),
                ('youtube_url', models.URLField(blank=True)),
                ('deskripsi_seo', models.CharField(blank=True, max_length=320)),
                ('teks_footer', models.CharField(default='Seluruh hak cipta dilindungi undang-undang.', max_length=200)),
                ('diperbarui', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Pengaturan Website',
                'verbose_name_plural': 'Pengaturan Website',
            },
        ),
    ]

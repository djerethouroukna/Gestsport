# Generated migration to fix QR field length
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0004_scan_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='qr_code',
            field=models.ImageField(
                upload_to='tickets/qr_codes/',
                blank=True,
                null=True,
                max_length=255,
                verbose_name='code QR'
            ),
        ),
    ]

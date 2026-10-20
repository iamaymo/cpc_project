from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cpc_app', '0003_alter_clients_phone_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='clients',
            name='password',
            field=models.CharField(default='', max_length=128),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='engineers',
            name='password',
            field=models.CharField(default='', max_length=128),
            preserve_default=False,
        ),
    ]


# Generated migration for Users model refactor

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cpc_app', '0004_clients_password_engineers_password'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Networks',
        ),
        migrations.DeleteModel(
            name='Clients',
        ),
        migrations.DeleteModel(
            name='Engineers',
        ),
        migrations.CreateModel(
            name='Users',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=100, verbose_name='الاسم الكامل')),
                ('phone_number', models.CharField(max_length=15, unique=True, verbose_name='رقم الهاتف')),
                ('username', models.CharField(blank=True, max_length=15, unique=True, verbose_name='اسم المستخدم')),
                ('password', models.CharField(max_length=128, verbose_name='كلمة المرور')),
                ('role', models.CharField(choices=[('ENGINEER', 'مهندس'), ('SALES', 'مبيعات'), ('ADMIN', 'إدارة'), ('ACCOUNTING', 'حسابات')], default='ENGINEER', max_length=20, verbose_name='الدور / الفريق')),
                ('add_at', models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')),
            ],
            options={
                'verbose_name': 'مستخدم',
                'verbose_name_plural': 'المستخدمون',
                'db_table': 'USERS',
            },
        ),
    ]


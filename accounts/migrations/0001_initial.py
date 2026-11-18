import accounts.models
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('user_id', models.AutoField(primary_key=True, serialize=False)),
                ('full_name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=255, unique=True)),
                ('password', models.CharField(db_column='password_hash', max_length=255, verbose_name='password')),
                ('role', models.CharField(choices=[('admin', 'Admin'), ('staff', 'Staff')], default='staff', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'db_table': 'user_account',
            },
            managers=[
                ('objects', accounts.models.UserManager()),
            ],
        ),
    ]

# Generated by Django 5.0.7 on 2024-08-29 13:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0020_client_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='project_start_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
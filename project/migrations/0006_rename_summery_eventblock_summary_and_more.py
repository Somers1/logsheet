# Generated by Django 5.0.7 on 2024-08-05 11:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0005_eventblock'),
    ]

    operations = [
        migrations.RenameField(
            model_name='eventblock',
            old_name='summery',
            new_name='summary',
        ),
        migrations.AlterField(
            model_name='eventblock',
            name='end_timestamp',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='eventblock',
            name='project',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='project.project'),
        ),
        migrations.AlterField(
            model_name='eventblock',
            name='start_timestamp',
            field=models.DateTimeField(null=True),
        ),
    ]

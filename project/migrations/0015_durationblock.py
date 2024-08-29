# Generated by Django 5.0.7 on 2024-08-28 13:52

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0014_project_harvest_project_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='DurationBlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('duration', models.DurationField()),
                ('summary', models.TextField(null=True)),
                ('project', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='project.project')),
            ],
        ),
    ]
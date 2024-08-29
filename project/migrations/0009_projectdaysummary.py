# Generated by Django 5.0.7 on 2024-08-07 02:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0008_remove_timesheetday_timesheet_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectDaySummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('summary', models.TextField()),
                ('date', models.DateField()),
                ('uploaded_to_harvest', models.BooleanField(default=False)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='project.project')),
            ],
        ),
    ]
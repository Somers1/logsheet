# Generated by Django 5.0.7 on 2024-08-01 02:31

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0002_timesheet'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='timesheet',
            name='response',
        ),
        migrations.AddField(
            model_name='timesheet',
            name='daily_html_format',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='TimesheetDay',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('html', models.TextField(blank=True, null=True)),
                ('timesheet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='project.timesheet')),
            ],
        ),
    ]

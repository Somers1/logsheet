# Generated by Django 5.0.7 on 2024-08-28 13:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0013_remove_project_monthly_hours_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='harvest_project_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
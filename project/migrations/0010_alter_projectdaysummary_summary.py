# Generated by Django 5.0.7 on 2024-08-07 02:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0009_projectdaysummary'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectdaysummary',
            name='summary',
            field=models.TextField(null=True),
        ),
    ]

# Generated by Django 5.1.1 on 2024-10-08 11:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_remove_game_region'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.category'),
        ),
    ]

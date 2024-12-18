# Generated by Django 5.1.1 on 2024-11-10 05:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0016_remove_category_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='is_fast_shipping',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='state',
            name='fast_shipping_price',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]

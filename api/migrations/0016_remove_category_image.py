# Generated by Django 5.0.6 on 2024-11-06 19:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0015_product_related_products'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='image',
        ),
    ]

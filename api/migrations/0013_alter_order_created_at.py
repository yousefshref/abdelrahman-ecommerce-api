# Generated by Django 5.1.1 on 2024-10-24 07:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0012_order_sales_who_added'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='created_at',
            field=models.DateField(auto_now_add=True),
        ),
    ]

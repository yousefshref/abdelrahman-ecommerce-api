# Generated by Django 5.1.3 on 2024-11-30 21:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0023_homepageimage_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(choices=[('cash', 'cash'), ('card', 'card'), ('instapay-ewallet', 'instapay-ewallet')], default='cash', max_length=100),
        ),
    ]
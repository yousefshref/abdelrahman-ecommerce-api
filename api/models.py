from django.db import models


from django.contrib.auth.models import AbstractUser


from django.utils.timezone import now  # Import this to get the current time


class CustomUser(AbstractUser):
    profile_picture = models.TextField(null=True, blank=True)  # Optional profile picture
    is_shipping_employee = models.BooleanField(default=False)
    commission = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.username



class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Product(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # Reference to the seller

    rank = models.IntegerField(null=True, blank=True)

    # basic infos
    # images = models.JSONField(null=True, blank=True)  # Image of the account or game
    image1 = models.ImageField(upload_to='images/', null=True, blank=True)
    image2 = models.ImageField(upload_to='images/', null=True, blank=True)
    image3 = models.ImageField(upload_to='images/', null=True, blank=True)
    image4 = models.ImageField(upload_to='images/', null=True, blank=True)

    name = models.CharField(max_length=100)  # Name of the game
    description = models.TextField()  # Description of the account, like what's included
    category = models.ForeignKey(Category, on_delete=models.CASCADE)  # Description of the account, like what's included

    # pricing
    price = models.IntegerField()  # Price of the account
    offer_price = models.IntegerField(null=True, blank=True)  # Offer price

    # stock managment
    stock = models.IntegerField()
    min_stock = models.IntegerField(null=True, blank=True)


    # related products
    related_products = models.ManyToManyField('self', blank=True, null=True, related_name='related_to')

    created_at = models.DateTimeField(auto_now_add=True)  # When the account was listed

    def __str__(self):
        return self.name





class State(models.Model):
    name = models.CharField(max_length=100)
    shipping_price = models.IntegerField()
    fast_shipping_price = models.IntegerField(null=True, blank=True)

    rank = models.IntegerField(null=True, blank=True, default=0)

    def __str__(self):
        return self.name



class Order(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)  # Reference to the buyer

    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=100)
    email = models.CharField(max_length=100, null=True, blank=True)
    state = models.ForeignKey('State', on_delete=models.CASCADE)
    address = models.CharField(max_length=100)

    is_fast_shipping = models.BooleanField(default=False)

    status = models.CharField(max_length=100, choices=[('pending', 'Pending'), ('processing', 'Processing'), ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')], default='pending')
    tracking_code = models.CharField(max_length=100, null=True, blank=True)
    sales_who_added = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sales', null=True, blank=True)

    total = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.pk) + " " + str(self.name)

    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

                


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()

    def __str__(self):
        return self.product.name



class HomePageImage(models.Model):
    image = models.ImageField(upload_to='images/')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)




from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Order)
def update_stock_on_cancel(sender, instance, **kwargs):
    """
    Adjust product stock when an order's status changes to 'cancelled'.
    """
    if instance.status == 'cancelled':
        # Iterate through the items in the order
        for item in instance.items.all():
            item.product.stock += item.quantity
            item.product.save()



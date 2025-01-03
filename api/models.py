from django.db import models

from django.contrib.auth.models import AbstractUser




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

    payment_method = models.CharField(max_length=100, default='cash', choices=[('cash', 'cash'), ('card', 'card'), ('instapay-ewallet', 'instapay-ewallet')])

    status = models.CharField(max_length=100, choices=[('pending', 'Pending'), ('processing', 'Processing'), ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')], default='pending')
    tracking_code = models.CharField(max_length=100, null=True, blank=True)
    sales_who_added = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sales', null=True, blank=True)

    total = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.pk) + " " + str(self.name)

    def get_total_price(self):
        total = 0
        for item in self.items.all():
            if item.product.offer_price:
                total += item.product.offer_price * item.quantity
            else:
                total += item.product.price * item.quantity
        
        total += self.state.shipping_price

        if self.is_fast_shipping and self.state.fast_shipping_price:
            total += self.state.fast_shipping_price

        self.total = total
    
    def save(self, *args, **kwargs):
        # super().save(*args, **kwargs)
        if self.pk:
            if self.status != "cancelled":
                self.get_total_price()
            
            if self.status == "cancelled":
                for item in self.items.all():
                    item.product.stock += item.quantity
                    item.quantity = 0
                    item.save_base()
                    item.product.save()
        else:
            print("new order")
        super().save(*args, **kwargs)
                


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()

    def __str__(self):
        return self.product.name
    
    
    def save(self, *args, **kwargs):
        # Handle stock adjustments
        if self.pk:  # If the OrderItem exists
            old_quantity = OrderItem.objects.get(pk=self.pk).quantity
            quantity_change = self.quantity - old_quantity
            self.product.stock -= quantity_change
        else:  # If this is a new OrderItem
            self.product.stock -= self.quantity
        
        if self.product.stock < 0:
            raise ValueError("Not enough stock for this product!")
        
        self.product.save()
        super().save(*args, **kwargs)
        self.order.save()
    
    def delete(self, *args, **kwargs):
        # Return the stock when the OrderItem is deleted
        self.product.stock += self.quantity
        self.product.save()
        super().delete(*args, **kwargs)


from django.db.models.signals import pre_delete
from django.dispatch import receiver

@receiver(pre_delete, sender=OrderItem)
def restore_stock_on_delete(sender, instance, **kwargs):
    instance.product.stock += instance.quantity
    instance.product.save()


class HomePageImage(models.Model):
    image = models.ImageField(upload_to='images/')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)




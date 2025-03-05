from django.db import models

from django.contrib.auth.models import AbstractUser


from django.db.models.signals import pre_delete
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache





class CustomUser(AbstractUser):
    profile_picture = models.TextField(null=True, blank=True)  # Optional profile picture
    is_shipping_employee = models.BooleanField(default=False)
    is_fast_shipping_employee = models.BooleanField(default=False)
    commission = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمين"

    def __str__(self):
        return self.username


class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "صنف"
        verbose_name_plural = "الأصناف"

    def __str__(self):
        return self.name


class Product(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, verbose_name="الصانع")  # Reference to the seller

    rank = models.IntegerField(null=True, blank=True, verbose_name="الترتيب")

    # basic infos
    # images = models.JSONField(null=True, blank=True)  # Image of the account or game
    image1 = models.ImageField(upload_to='images/', null=True, blank=True, verbose_name="صورة 1")
    image2 = models.ImageField(upload_to='images/', null=True, blank=True, verbose_name="صورة 2")
    image3 = models.ImageField(upload_to='images/', null=True, blank=True, verbose_name="صورة 3")
    image4 = models.ImageField(upload_to='images/', null=True, blank=True, verbose_name="صورة 4")

    name = models.CharField(max_length=100, verbose_name="اسم المنتج")  # Name of the game
    description = models.TextField(verbose_name="وصف")  # Description of the account, like what's included
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="الصنف")  # Description of the account, like what's included

    # pricing
    price = models.IntegerField(verbose_name="سعر")  # Price of the account
    offer_price = models.IntegerField(null=True, blank=True, verbose_name="سعر العرض")  # Offer price

    # stock managment
    stock = models.IntegerField(verbose_name="الكمية المتوفرة")
    min_stock = models.IntegerField(null=True, blank=True, verbose_name="الحد الادنى للكمية المتوفرة")


    # related products
    related_products = models.ManyToManyField('self', blank=True, null=True, related_name='related_to')

    created_at = models.DateTimeField(auto_now_add=True)  # When the account was listed

    class Meta:
        verbose_name = "منتج"
        verbose_name_plural = "المنتجات"

    def __str__(self):
        return self.name


class State(models.Model):
    name = models.CharField(max_length=100)
    shipping_price = models.IntegerField()
    fast_shipping_price = models.IntegerField(null=True, blank=True)

    rank = models.IntegerField(null=True, blank=True, default=0)

    class Meta:
        verbose_name = "محافظة"
        verbose_name_plural = "المحافظات"

    def __str__(self):
        return self.name


class Order(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, verbose_name="المشتري")
    name = models.CharField(max_length=100, verbose_name="الاسم")
    phone_number = models.CharField(max_length=100, verbose_name="رقم الهاتف")
    email = models.CharField(max_length=100, null=True, blank=True, verbose_name="البريد الإلكتروني")
    state = models.ForeignKey('State', on_delete=models.CASCADE, verbose_name="المحافظة")
    address = models.CharField(max_length=100, verbose_name="العنوان")

    is_fast_shipping = models.BooleanField(default=False, verbose_name="شحن سريع")

    payment_method = models.CharField(
        max_length=100, default='cash',
        choices=[('cash', 'نقدي'), ('card', 'بطاقة'), ('instapay-ewallet', 'محفظة إلكترونية')],
        verbose_name="طريقة الدفع"
    )

    status = models.CharField(
        max_length=100,
        choices=[('pending', 'قيد الانتظار'), ('processing', 'تحت المعالجة'), ('shipped', 'تم الشحن'),
                 ('delivered', 'تم التوصيل'), ('cancelled', 'ملغى')],
        default='pending',
        verbose_name="الحالة"
    )
    tracking_code = models.CharField(max_length=100, null=True, blank=True, verbose_name="كود التتبع")
    sales_who_added = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='sales',
        null=True, blank=True, verbose_name="السيلر"
    )

    total = models.IntegerField(null=True, blank=True, verbose_name="الإجمالي", default=0)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات"

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

    def check_seller(self, user):
        """
        Checks if the current user is a seller (shipping employee or fast shipping employee)
        and then, based on the conditions, sets the sales_who_added field.
        
        For a shipping employee:
        - If there is no previous order or the previous order's tracking_code is different 
        from the new tracking_code, and no seller is recorded yet, record the user.
        
        For a fast shipping employee:
        - If there is no previous order or the new status is different from the current order status,
        record the user.
        """
        # Ensure we have a user
        if not user:
            return

        try:
            previous = Order.objects.get(pk=self.pk)
        except Order.DoesNotExist:
            previous = None

        # For a shipping employee:
        if getattr(user, "is_shipping_employee", False):
            # Only update if the order exists and the new tracking code is not empty.
            if self.tracking_code and (self.tracking_code != getattr(previous, "tracking_code", None)):
                self.sales_who_added = user

        # For a fast shipping employee:
        if self.pk and getattr(user, "is_fast_shipping_employee", False) and not self.sales_who_added and self.status != getattr(previous, "status", None):
            self.sales_who_added = user

        if getattr(user, "is_fast_shipping_employee", False) and not self.sales_who_added and self.status != getattr(previous, "status", None) and self.status != 'pending':
            self.sales_who_added = user





    def save(self, *args, **kwargs):
        user = None
        try:
            user = self.req_user
        except:
            pass

        # Now use `user` for custom logic without modifying order.user
        if self.pk:  # Update
            if self.status != "cancelled":
                self.get_total_price()
            # if self.status == "cancelled":
            #     for item in self.items.all():
            #         item.product.stock += int(item.quantity)
            #         item.quantity = 0
            #         item.save_base()
            #         item.product.save()
            self.check_seller(user)  # Pass the logged-in user for seller checks
        else:  # Create
            print("New order")
            self.check_seller(user)

        super().save(*args, **kwargs)





class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.IntegerField(null=True, blank=True, default=0)

    class Meta:
        verbose_name = "تفاصيل اوردر"
        verbose_name_plural = "تفاصيل الاوردرات"

    def __str__(self):
        return self.product.name
    
    
    def save(self, *args, **kwargs):
        # if self.pk:
        if self.order.status != "cancelled":
            self.price = self.product.offer_price * self.quantity if self.product.offer_price else self.product.price * self.quantity
        # # Handle stock adjustments
        # if self.pk:  # If the OrderItem exists
        #     old_quantity = OrderItem.objects.get(pk=self.pk).quantity
        #     quantity_change = int(self.quantity) - int(old_quantity)
        #     self.product.stock -= int(quantity_change)
        # else:  # If this is a new OrderItem
        #     self.product.stock -= int(self.quantity)
        
        # if self.product.stock < 0:
        #     raise ValueError("Not enough stock for this product!")
        
        # self.product.save()
        super().save(*args, **kwargs)
        # self.order.save()
    


# @receiver(pre_delete, sender=OrderItem)
# def restore_stock_on_delete(sender, instance, **kwargs):
#     instance.product.stock += instance.quantity
#     instance.product.save()



class HomePageImage(models.Model):
    image = models.ImageField(upload_to='images/')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = "صفحة رئيسية"
        verbose_name_plural = "الصفحة الرئيسية"


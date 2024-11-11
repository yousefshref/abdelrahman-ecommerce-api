from django.contrib import admin

from .models import CustomUser,  Category, Product,State, Order, OrderItem, HomePageImage


admin.site.register(CustomUser)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(State)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(HomePageImage)


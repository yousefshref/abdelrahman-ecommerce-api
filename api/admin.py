from django.contrib import admin

from .models import CustomUser,  Category, Product,State, Order, OrderItem, HomePageImage


admin.site.register(CustomUser)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(State)


def duplicate_order(modeladmin, request, queryset):
    for order in queryset:
        order_items = order.items.all()
        order.pk = None
        order.save()
        for item in order_items:
            item.pk = None
            item.order = order
            item.save()

duplicate_order.short_description = "Duplicate selected orders"

class OrderAdmin(admin.ModelAdmin):
    actions = [duplicate_order]

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)

admin.site.register(HomePageImage)


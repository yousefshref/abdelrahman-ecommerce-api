from rest_framework import serializers

from .models import CustomUser, Category, Product, State, Order, OrderItem


class UserSerializer(serializers.ModelSerializer):
    class Meta():
        model = CustomUser 
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    class Meta():
        model = Category
        fields = "__all__"


class ProductSerializerForProduct(serializers.ModelSerializer):
    user_details = UserSerializer(read_only=True, source='user')
    category_details = CategorySerializer(read_only=True, source='category')
    class Meta():
        model = Product
        fields = "__all__"

class ProductSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(read_only=True, source='user')
    category_details = CategorySerializer(read_only=True, source='category')
    related_products_details = ProductSerializerForProduct(many=True, read_only=True , source='related_products')
    class Meta():
        model = Product
        fields = "__all__"


class StateSerializer(serializers.ModelSerializer):
    class Meta():
        model = State
        fields = "__all__"




class OrderItemSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(read_only=True, source='product')
    class Meta():
        model = OrderItem
        fields = "__all__"

class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True , source='items')
    user_details = UserSerializer(read_only=True, source='user')
    state_details = StateSerializer(read_only=True, source='state')
    sales_who_added_details = UserSerializer(read_only=True, source='sales_who_added')
    class Meta():
        model = Order
        fields = "__all__"



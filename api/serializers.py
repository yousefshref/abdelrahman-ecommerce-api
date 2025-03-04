from rest_framework import serializers

from .models import CustomUser, Category, Product, State, Order, OrderItem, HomePageImage


from django.contrib.auth import authenticate


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
    class Meta():
        model = Product
        fields = "__all__"


class SingleProductSerializer(serializers.ModelSerializer):
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





class HomePageImageSerializer(serializers.ModelSerializer):
    class Meta():
        model = HomePageImage
        fields = "__all__"




class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")
        user = authenticate(email=email, password=password)
        if user is None:
            raise serializers.ValidationError("Invalid credentials")
        data["user"] = user
        return data


# Serializer for registration
class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = '__all__'

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user



from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token

from .serializers import UserSerializer, ProductSerializer, StateSerializer, CategorySerializer, OrderSerializer, OrderItemSerializer, HomePageImageSerializer
from .models import CustomUser, Product, State, Order, OrderItem, Category, HomePageImage



@api_view(['POST'])
def signup(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        user = CustomUser.objects.get(username=request.data['username'])
        user.set_password(request.data['password'])
        user.save()
        token = Token.objects.create(user=user)
        return Response({'token': token.key, 'user': serializer.data})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def login(request):
    user = get_object_or_404(CustomUser, username=request.data['username'])
    if not user.check_password(request.data['password']):
        return Response("missing user", status=status.HTTP_404_NOT_FOUND)
    token, created = Token.objects.get_or_create(user=user)
    serializer = UserSerializer(user)
    return Response({'token': token.key, 'user': serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([AllowAny])
def user(request):
    if request.user.is_authenticated:
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    else:
        return Response('You are not authenticated', status=status.HTTP_401_UNAUTHORIZED)



@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([AllowAny])
def get_user(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    serializer = UserSerializer(user)
    return Response(serializer.data)

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_products(request):
    products = Product.objects.all().order_by('-id')

    # search
    search = request.GET.get('search')
    if search:
        products = products.filter(name__icontains=search)

    # category
    category = request.GET.get('category')
    if category:
        products = products.filter(category__id=category)

    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    serializer = ProductSerializer(product)
    return Response(serializer.data)



@api_view(['GET', 'POST'])
def states_list(request):
    if request.method == 'GET':
        states = State.objects.all().order_by('name')
        serializer = StateSerializer(states, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = StateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def state_detail(request, pk):
    try:
        state = State.objects.get(pk=pk)
    except State.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = StateSerializer(state)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = StateSerializer(state, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        state.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

# create order funtion
from django.db import transaction

@api_view(['POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([AllowAny])
def create_order(request):
    
    data = request.data.copy()
    
    if request.user.is_authenticated:
        data['user'] = request.user.id
    else:
        data['user'] = None

    serializer = OrderSerializer(data=data)
    if serializer.is_valid():
        order = serializer.save()


        order_items = request.data['order_items']
        for item in order_items:
            item['order'] = order.id
            ser = OrderItemSerializer(data=item)
            if ser.is_valid():
                ser.save()

                product = get_object_or_404(Product, id=item['product'])

                if int(product.stock) < int(item['quantity']):
                    order.delete()
                    return Response(f'هذا المنتج غير متوفر في المخزن: {product.name}, برجاء تخفيف العدد المطلوب او حذفه من السلة', status=status.HTTP_400_BAD_REQUEST)
                else:
                    product.stock -= int(item['quantity'])
                    product.save()

                    # return Response(ser.data, status=status.HTTP_201_CREATED)
            else:
                return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)









# admin

@api_view(['GET'])
def get_categories(request):
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def create_category(request):
    serializer = CategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
def update_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    serializer = CategorySerializer(category, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def create_product(request):
    if request.method == 'POST':
        data = request.data.copy()
        data['user'] = request.user.id
        serializer = ProductSerializer(data=data)
        if serializer.is_valid():
            product = serializer.save()
            
            # get related products
            related_products = request.data.get('related_products_data', [])

            if isinstance(related_products, str):
                related_products = list(map(int, filter(None, related_products.split(','))))

            

            if related_products:
                for rp in related_products:
                    related_product = get_object_or_404(Product, id=rp)
                    product.related_products.add(related_product)
            else:
                product.related_products.clear()

            product.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['PUT'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    serializer = ProductSerializer(product, data=request.data, partial=True)
    if serializer.is_valid():
        product = serializer.save()
        
        # get related products
        related_products = request.data.get('related_products_data', [])

        if isinstance(related_products, str):
            related_products = list(map(int, filter(None, related_products.split(','))))

        if related_products:
            for rp in related_products:
                related_product = get_object_or_404(Product, id=rp)
                product.related_products.add(related_product)
        else:
            product.related_products.clear()

        product.save()
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)




@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_sales_users(request):
    users = CustomUser.objects.filter(is_shipping_employee=True).order_by('-id')
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)



from django.db.models import Q

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_orders(request):
    orders = Order.objects.all().order_by('-id')

    # sales orders
    sales_id = request.GET.get('sales_id')
    if sales_id:
        orders = orders.filter(sales_who_added__pk=sales_id)

    # id and name and phone
    search = request.GET.get('search')
    if search:
        orders = orders.filter(Q(id__icontains=search) | Q(name__icontains=search) | Q(phone_number__icontains=search))

    # status
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)

    # from 
    from_date = request.GET.get('from')
    if from_date:
        orders = orders.filter(created_at__gte=from_date)

    # to
    to_date = request.GET.get('to')
    if to_date:
        orders = orders.filter(created_at__lte=to_date)

    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)



@api_view(['PUT'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    data = request.data.copy()

    serializer = OrderSerializer(order, data=data, partial=True)
    if serializer.is_valid():
        # Track order items from the request
        order_items_data = data.get('order_items', [])
        
        # Dictionary to track existing OrderItem objects
        existing_items = {item.id: item for item in order.items.all()}
        
        for item_data in order_items_data:
            product_id = item_data.get('product')
            quantity = item_data.get('quantity', 0)
            
            try:
                # Check if the OrderItem already exists
                order_item = OrderItem.objects.get(order=order, product_id=product_id)
                
                # Update the quantity and check stock availability
                if int(quantity) > int(order_item.quantity):
                    additional_quantity_needed = int(quantity) - int(order_item.quantity)
                    if int(order_item.product.stock) < int(additional_quantity_needed):
                        return Response({'error': f'Insufficient stock for product {order_item.product.name}'}, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Reduce stock
                    order_item.product.stock -= additional_quantity_needed
                elif int(quantity) < int(order_item.quantity):
                    # Increase stock back if the new quantity is less
                    stock_difference = int(order_item.quantity) - int(quantity)
                    order_item.product.stock += int(stock_difference)
                
                # Update the order item quantity
                order_item.quantity = int(quantity)
                order_item.save()
                order_item.product.save()
                existing_items.pop(order_item.id, None)  # Remove from existing items tracker
                
            except OrderItem.DoesNotExist:
                # Handle new OrderItem creation
                product = get_object_or_404(Product, pk=product_id)
                
                if int(product.stock) < int(quantity):
                    return Response({'error': f'Insufficient stock for product {product.name}'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Create new OrderItem and reduce stock
                OrderItem.objects.create(order=order, product=product, quantity=quantity)
                product.stock -= int(quantity)
                product.save()
        
        # Delete any OrderItems that are not included in the request data
        for remaining_item in existing_items.values():
            remaining_item.product.stock += remaining_item.quantity  # Restore stock
            remaining_item.product.save()
            remaining_item.delete()
        
        # Save the order after processing items
        order = serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['DELETE'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def delete_order(request, pk):
    order = get_object_or_404(Order, pk=pk)

    # Restore stock for each order item
    for item in order.items.all():
        product = item.product
        product.stock += item.quantity  # Restore the stock
        product.save()

    # Delete the order after restoring the stock
    order.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)



@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_users(request):
    users = CustomUser.objects.all().order_by('-id')
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['PUT'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_user(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_user_password(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        user.set_password(serializer.validated_data['password'])
        user.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(sender_email, sender_password, recipient_email, subject, message):
    try:
        # Set up the MIME
        email_msg = MIMEMultipart()
        email_msg['From'] = sender_email
        email_msg['To'] = recipient_email
        email_msg['Subject'] = subject

        # Attach message to email
        email_msg.attach(MIMEText(message, 'plain'))

        # SMTP server configuration
        smtp_server = "smtp.gmail.com"  # Use appropriate SMTP server (e.g., Gmail, Outlook)
        smtp_port = 587  # Port for TLS

        # Set up the server and send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable TLS for security
        server.login(sender_email, sender_password)
        text = email_msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        
        server.quit()  # Disconnect from the server
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")



@api_view(['POST'])
def send_email_to_sales_with_his_target(request):
    date_from = request.data.get('date_from')
    date_to = request.data.get('date_to')
    # get the user
    user = CustomUser.objects.get(id=request.data['user_id'])
    # get the order that contains the user id
    orders = Order.objects.filter(sales_who_added=user)
    if date_from and date_to:
        orders = orders.filter(created_at__range=[date_from, date_to])
    # get the total of user commissions
    user_commission = int(user.commission)
    # get the total of orders

    total_orders = 0
    for order in orders:
        total = 0

        order_items = OrderItem.objects.filter(order=order)
        
        for order_item in order_items:
            order_item_price = 0
            if order_item.product.offer_price:
                order_item_price = order_item.product.offer_price
            else:
                order_item_price = order_item.product.price

            total += int(order_item_price * order_item.quantity)

        state_details = State.objects.get(id=order.state.id)
        total += int(state_details.shipping_price)

        if(order.is_fast_shipping):
            total += int(state_details.fast_shipping_price)

        total_orders += total
    
    total_after_commissions = total_orders * (100 - user_commission) / 100

    # send email to him with report of his target

    send_email(
        sender_email='abdelrahmanmashaly779@gmail.com',
        sender_password='xkiz irbq vdtf qzwn',
        recipient_email=user.email,
        subject='Your target report',
        message=f'Your total orders: {total_orders}\nYour commission: {user_commission}\nYour total after commissions: {total_after_commissions}'
    )

    return Response(status=status.HTTP_200_OK)





@api_view(['GET'])
def home_page_images(request):
    images = HomePageImage.objects.all()
    serializer = HomePageImageSerializer(images, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def create_home_page_image(request):
    serializer = HomePageImageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def delete_home_page_image(request, pk):
    image = get_object_or_404(HomePageImage, pk=pk)
    image.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)





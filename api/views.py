from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response
from rest_framework import status

from django.core.cache import cache


from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token

from .serializers import UserSerializer, ProductSerializer, StateSerializer, CategorySerializer, OrderSerializer, OrderItemSerializer, HomePageImageSerializer, SingleProductSerializer
from .models import CustomUser, Product, State, Order, OrderItem, Category, HomePageImage

from django.conf import settings

from google.oauth2 import id_token
from google.auth.transport import requests

from datetime import timedelta
from django.utils.timezone import now


import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText




# front_end_url = "http://localhost:5173"
# front_end_url = "https://abdelrahman-ecommerce-front.vercel.app"
front_end_url = "https://safe-zone.store"


# back_end_url = "http://127.0.0.1:8000/"
back_end_url = "https://abdelrahmanecommerce.pythonanywhere.com/"



def send_email(recipient_email, subject, message, content_type="plain"):
    sender_email = "saffezone.store@gmail.com"
    sender_password = "rxjk uhro oyac eqhe"
    try:
        # Set up the MIME
        email_msg = MIMEMultipart()
        email_msg['From'] = sender_email
        email_msg['To'] = recipient_email
        email_msg['Subject'] = subject

        # Attach the message based on the content type
        email_msg.attach(MIMEText(message, content_type))

        # SMTP server configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

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
def send_email_function_api(request):
    data = request.data.copy()
    send_email(data['recipient_email'], data['subject'], data['message'], data['content_type'])
    return Response("Email sent successfully!", status=status.HTTP_200_OK)



@api_view(['POST'])
def google_auth_view(request):
    token = request.data.get("token")
    try:
        # Verify the token with Google's API
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)

        # Extract user info
        email = idinfo.get("email")
        name = idinfo.get("name")

        # Get or create the user
        user, created = CustomUser.objects.get_or_create(email=email, defaults={"username": name})
    
        # Get or create the token
        token, _ = Token.objects.get_or_create(user=user)

        # Return the user or a token for further sessions
        return Response({"message": "Authenticated", "user": UserSerializer(user).data, "token": token.key}, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response({"error": "Invalid Token"}, status=status.HTTP_400_BAD_REQUEST)


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
    username = request.data.get('username')
    password = request.data.get('password')

    user = CustomUser.objects.filter(Q(username=username) | Q(email=username)).first()
    if user is None or not user.check_password(password):
        return Response("Invalid credentials", status=status.HTTP_404_NOT_FOUND)

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


@api_view(['DELETE'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([AllowAny])
def delete_user(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    user.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([AllowAny])
def get_user(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    serializer = UserSerializer(user)
    return Response(serializer.data)


# from django.db.models import Q, F

# @api_view(['GET'])
# @authentication_classes([SessionAuthentication, TokenAuthentication])
# @permission_classes([IsAuthenticatedOrReadOnly])
# def get_products(request):
#     products = Product.objects.all().order_by('rank')

#     # search
#     search = request.GET.get('search')
#     if search:
#         products = products.filter(name__icontains=search)

#     # category
#     category = request.GET.get('category')
#     if category:
#         products = products.filter(category__id=category)

#     about_to_end = request.GET.get('about_to_end')
#     if about_to_end:
#         products = products.filter(Q(min_stock__isnull=False) & Q(stock__lte=F('min_stock')))


#     serializer = ProductSerializer(products, many=True)
#     return Response(serializer.data)


# @api_view(['GET'])
# @authentication_classes([SessionAuthentication, TokenAuthentication])
# @permission_classes([IsAuthenticatedOrReadOnly])
# def get_product(request, pk):
#     product = get_object_or_404(Product, pk=pk)
#     serializer = ProductSerializer(product)
#     return Response(serializer.data)

CACHE_TIMEOUT = None

def get_cached_products(search=None, category=None, about_to_end=None):
    cache_key = "products_list"
    
    if search:
        cache_key += f"_search{search}"
    if category:
        cache_key += f"_category{category}"
    if about_to_end:
        cache_key += f"_abouttoend{about_to_end}"
    
    cached_products = cache.get(cache_key)
    
    if not cached_products:
        print('Fetching products from database')
        products = Product.objects.all().order_by('rank')

        if search:
            products = products.filter(name__icontains=search)

        if category:
            products = products.filter(category__id=category)

        if about_to_end:
            products = products.filter(Q(min_stock__isnull=False) & Q(stock__lte=F('min_stock')))

        serializer = ProductSerializer(products, many=True)
        cached_products = serializer.data
        cache.set(cache_key, cached_products, timeout=CACHE_TIMEOUT)  # Cache the data
    else:
        print('Fetching products from cache')

    return cached_products

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_products(request):
    search = request.GET.get('search')
    category = request.GET.get('category')
    about_to_end = request.GET.get('about_to_end')
    
    products = get_cached_products(search, category, about_to_end)
    return Response(products)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_product(request, pk):
    cache_key = f"product_{pk}"
    cached_product = cache.get(cache_key)

    if cached_product is None:
        product = get_object_or_404(Product, pk=pk)
        serializer = SingleProductSerializer(product)
        cached_product = serializer.data
        cache.set(cache_key, cached_product, timeout=CACHE_TIMEOUT)  # Cache the data

    return Response(cached_product)



@api_view(['GET', 'POST'])
def states_list(request):
    if request.method == 'GET':
        states = State.objects.all().order_by('rank')
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
# @authentication_classes([TokenAuthentication, SessionAuthentication])
@authentication_classes([TokenAuthentication])
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

        send_shipped_email = False
        if data.get('status') == 'shipped':
            send_shipped_email = True

        send_delivered_email = False
        if data.get('status') == 'delivered':
            send_delivered_email = True

        order_items = request.data['order_items']
        for item in order_items:
            item['order'] = order.id
            ser = OrderItemSerializer(data=item)
            if ser.is_valid():
                ser.save()

                # product = get_object_or_404(Product, id=item['product'])

                # if int(product.stock) < int(item['quantity']):
                #     order.delete()
                #     return Response(f'هذا المنتج غير متوفر في المخزن: {product.name}, برجاء تخفيف العدد المطلوب او حذفه من السلة', status=status.HTTP_400_BAD_REQUEST)
                # else:
                #     product.stock -= int(item['quantity'])
                #     product.save()

                    # return Response(ser.data, status=status.HTTP_201_CREATED)
            else:
                return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        order_obj = Order.objects.get(id=order.id)
        order_items = OrderItem.objects.filter(order=order_obj)

        # Sample variables to include in the email
        customer_name = order_obj.name
        order_date = order_obj.created_at
        order_total = 0

        for item in order_items:
            price = 0
            if item.product.offer_price:
                price = item.product.offer_price
            else:
                price = item.product.price

            order_total += price * item.quantity
        
        shipping_cost = State.objects.get(id=order_obj.state.pk).shipping_price
        order_total += shipping_cost

        if order_obj.is_fast_shipping:
            fast_shipping_cost = State.objects.get(id=order_obj.state.pk).fast_shipping_price
            order_total += fast_shipping_cost

        
        # Construct the HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
            </style>
        </head>
        <body>
            <h1>Hello {customer_name},</h1>
            <p>Thank you for your order placed on {order_date}.</p>
            <p>Here are the details of your order:</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Item</th>
                        <th>Quantity</th>
                        <th>Price</th>
                    </tr>
                </thead>
                <tbody>
        """

        # Add each order item to the email body
        for item in order_items:
            price = 0
            if item.product.offer_price:
                price = item.product.offer_price
            else:
                price = item.product.price
            html_content += f"""
                    <tr>
                        <td>{item.product.name}</td>
                        <td>{item.quantity}</td>
                        <td>{price * item.quantity} EGP</td>
                    </tr>
            """

        # Close the HTML content
        html_content += f"""
                </tbody>
            </table>
            <p>If you want to cancel your order, please visit <a style="color: blue;" href="{front_end_url}/orders/cancel/?order_id={order_obj.id}&email={order_obj.email}">this link</a> before 24 hours of placing your order.</p>
            <p><strong>Total:</strong> {order_total} EGP</p>
            <p>We hope to see you again soon!</p>
        </body>
        </html>
        """
        if order_obj.email:
            send_email(
                    recipient_email=order_obj.email,
                    subject='تم انشاء طلبك',
                    message=html_content,
                    content_type="html"
                )
            

        # i want to check if the status data that comes from request is !== to the current status of the order and if it is then i want to send an email to the user
        if order.status == 'delivered' and order.email and order.tracking_code and send_delivered_email:
            send_email(
                recipient_email=order.email,
                subject="تم تسليم شحنتك",
                message=f"""
                    <h2>تم تسليم شحنتك</h2>
                    <p style="margin-top: 15px">
                        تم تسليم الشحنة للمندوب وترقب وصولها اليوم من الساعة 9 صباحا حتى الساعة 9 مساءً
                    </p>
                    <p style="margin-top: 10px">
                        يمكنك تتبع الطلب من خلال هذا الكود {order.tracking_code}, من خلال <a href={front_end_url + '/orders/track/'}>هذه الصفحة</a>
                    </p>
                """,
                content_type="html"
            )
            print('email sent', order.email)

        if order.status == 'shipped' and order.email and order.tracking_code and send_shipped_email:
            send_email(
                recipient_email=order.email,
                subject="تم شحن طلبك",
                message=f"""
                    <h2>تم تغيير حالة الطلب وسيتم توصيلة قريبا</h2>
                    <p style="margin-top: 15px">
                        تم شحن طلبك, ترقب مكالمة المندوب في اي وقت قريب
                    </p>
                    <p style="margin-top: 10px">
                        يمكنك تتبع الطلب من خلال هذا الكود {order.tracking_code}, من خلال <a href=${front_end_url + '/orders/track/'}>هذه الصفحة</a>
                    </p>
                """,
                content_type="html"
            )
            print('email sent', order.email)

        
        # check the sales user if added new tracking code
        if request.user.is_authenticated:
            if request.user.is_shipping_employee:
                order.sales_who_added = request.user
                order.save()

        
        # calculate total order
        # order_total = 0
        # for item in order_items:
        #     if item.product.offer_price:
        #         order_total += item.product.offer_price * item.quantity
        #     else:
        #         order_total += item.product.price * item.quantity
            
        # order_total += order.state.shipping_price

        # if order.is_fast_shipping:
        #     order_total += order.state.fast_shipping_price

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
        data = request.data
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
from django.db.models import Sum, F

# def get_cached_orders():
#     version = cache.get('order_version', 1)
#     orders = cache.get(f'all_orders_v{version}')
#     if not orders:
#         orders = list(Order.objects.all().order_by('-id'))
#         cache.set(f'all_orders_v{version}', orders, timeout=60 * 60)  # Cache for 1 hour
#     return orders

# @api_view(['GET'])
# @authentication_classes([SessionAuthentication, TokenAuthentication])
# @permission_classes([IsAuthenticated])
# def get_orders(request):
#     orders = Order.objects.all().order_by('-id')

#     # chaeck if the user is not admin
#     user = request.user

#     if user.is_staff == False:
#         orders = orders.filter(user=user)

#     # if user.is_shipping_employee == False:
#     #     orders = orders.filter(user=user)

#     # Filter by sales_id if provided
#     sales_id = request.GET.get('sales_id')

#     orders_total_commission = 0
#     total_orders_prices = 0

#     if sales_id:
#         orders = orders.filter(sales_who_added__pk=sales_id)

#         user = CustomUser.objects.get(id=sales_id)
#         for order in orders:
#             if order.total:
#                 orders_total_commission += int(order.total * user.commission / 100)

#         for order in orders:
#             if order.total:
#                 total_orders_prices += int(order.total)

#     # id and name and phone
#     search = request.GET.get('search')
#     if search:
#         # orders = [order for order in orders if search.lower() in str(order.id).lower() or search.lower() in order.name.lower() or search.lower() in order.phone_number.lower()]
#         orders = orders.filter(Q(id__icontains=search) | Q(name__icontains=search) | Q(phone_number__icontains=search))

#     # status
#     status = request.GET.get('status')
#     if status:
#         # orders = [order for order in orders if order.status == status]
#         orders = orders.filter(status=status)


#     if not sales_id:
#         for order in orders:
#             if order.total:
#                 total_orders_prices += int(order.total)

#     # Prepare response data
#     data = {
#         'orders': OrderSerializer(orders, many=True).data,
#         'total_orders_prices': total_orders_prices,
#         'total_commission': orders_total_commission
#     }

#     return Response(data)


# from django.core.cache import cache
# from django.db.models import Q
# from rest_framework.response import Response
# from rest_framework.decorators import api_view, authentication_classes, permission_classes
# from rest_framework.authentication import SessionAuthentication, TokenAuthentication
# from rest_framework.permissions import IsAuthenticated

# def get_cached_orders(version, user, sales_id=None, search=None, status=None):
#     cache_key = f'all_orders_v{version}_user{user.id}'
    
#     # Cache by sales_id, search, and status as well to handle different filtering
#     if sales_id:
#         cache_key += f'_sales{sales_id}'
#     if search:
#         cache_key += f'_search{search}'
#     if status:
#         cache_key += f'_status{status}'
    
#     orders = cache.get(cache_key)
    
#     if not orders:
#         orders = Order.objects.all().order_by('-id')

#         # If the user is not an admin, filter orders by user
#         if not user.is_staff:
#             orders = orders.filter(user=user)

#         # Filter by sales_id if provided
#         if sales_id:
#             orders = orders.filter(sales_who_added__pk=sales_id)

#         # Apply search filter
#         if search:
#             orders = orders.filter(Q(id__icontains=search) | Q(name__icontains=search) | Q(phone_number__icontains=search))

#         # Apply status filter
#         if status:
#             orders = orders.filter(status=status)

#         # Cache the orders with a timeout of 1 hour
#         cache.set(cache_key, list(orders), timeout=60 * 60)

#     return orders

# @api_view(['GET'])
# @authentication_classes([SessionAuthentication, TokenAuthentication])
# @permission_classes([IsAuthenticated])
# def get_orders(request):
#     user = request.user
#     version = cache.get('order_version', 1)  # You can update this version number when the orders data changes
    
#     # Fetch cached orders based on filters
#     sales_id = request.GET.get('sales_id')
#     search = request.GET.get('search')
#     status = request.GET.get('status')

#     # Get the cached orders or fetch fresh ones if not cached
#     orders = get_cached_orders(version, user, sales_id, search, status)
    
#     # Calculate the total commission and order prices
#     orders_total_commission = 0
#     total_orders_prices = 0

#     if sales_id:
#         user = CustomUser.objects.get(id=sales_id)
#         for order in orders:
#             if order.total:
#                 orders_total_commission += int(order.total * user.commission / 100)

#     for order in orders:
#         if order.total:
#             total_orders_prices += int(order.total)

#     # Prepare response data
#     data = {
#         'orders': OrderSerializer(orders, many=True).data,
#         'total_orders_prices': total_orders_prices,
#         'total_commission': orders_total_commission
#     }

#     return Response(data)


from django.core.cache import cache
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination  # Import pagination class

# Define a custom pagination class
class OrdersPagination(PageNumberPagination):
    page_size = 10  # Default number of orders per page
    page_size_query_param = 'page_size'  # Allow clients to set the page size
    max_page_size = 100  # Maximum page size limit

def get_cached_orders(version, user, sales_id=None, search=None, status=None, fast_shipping=False):
    cache_key = f'all_orders_v{version}_user{user.id}'
    
    # Cache by sales_id, search, and status as well to handle different filtering
    if sales_id:
        cache_key += f'_sales{sales_id}'
    if search:
        cache_key += f'_search{search}'
    if status:
        cache_key += f'_status{status}'
    if fast_shipping:
        cache_key += f'_fast_shipping{fast_shipping}'
    
    orders = cache.get(cache_key)
    
    if not orders:
        orders = Order.objects.all().order_by('-id')

        # If the user is not an admin, filter orders by user
        if not user.is_staff:
            orders = orders.filter(user=user)

        # Filter by sales_id if provided
        if sales_id:
            orders = orders.filter(sales_who_added__pk=sales_id)

        # Apply search filter
        if search:
            orders = orders.filter(Q(id__icontains=search) | Q(name__icontains=search) | Q(phone_number__icontains=search))

        # Apply status filter
        if status:
            orders = orders.filter(status=status)

        if fast_shipping:
            orders = orders.filter(is_fast_shipping=fast_shipping)

        # Cache the orders with a timeout of 1 hour
        cache.set(cache_key, list(orders), timeout=60 * 60)

    return orders

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_orders(request):
    user = request.user
    version = cache.get('order_version', 1)  # You can update this version number when the orders data changes
    
    # Fetch cached orders based on filters
    sales_id = request.GET.get('sales_id')
    search = request.GET.get('search')
    status = request.GET.get('status')

    # Get the cached orders or fetch fresh ones if not cached
    fast_shipping_only = False
    if user.is_fast_shipping_employee:
        fast_shipping_only = True

    orders = get_cached_orders(version, user, sales_id, search, status, fast_shipping_only)

    # Initialize pagination
    paginator = OrdersPagination()
    paginated_orders = paginator.paginate_queryset(orders, request)

    # Calculate the total commission and order prices
    orders_total_commission = 0
    total_orders_prices = 0

    if sales_id:
        user = CustomUser.objects.get(id=sales_id)
        for order in paginated_orders:
            if order.total:
                orders_total_commission += int(int(order.total) * int(user.commission) / 100)

    for order in paginated_orders:
        if order.total:
            total_orders_prices += int(order.total)

    # Prepare response data
    data = {
        'orders': OrderSerializer(paginated_orders, many=True).data,
        'total_orders_prices': total_orders_prices,
        'total_commission': orders_total_commission,
        'count': paginator.page.paginator.count,  # Total number of orders
        'next': paginator.get_next_link(),  # URL for the next page
        'previous': paginator.get_previous_link()  # URL for the previous page
    }

    return paginator.get_paginated_response(data)



@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_latest_client_orders(request):
    user = request.user

    if not user.is_authenticated:
        return Response({"error": "You are not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
    
    orders = get_cached_orders()
    orders = [order for order in orders if order.user.pk == user.id]
    seven_days_ago = now() - timedelta(days=7)
    orders = [order for order in orders if order.created_at >= seven_days_ago]
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def deliverd_orders_client(request):
    user = request.user

    if not user.is_authenticated:
        return Response({"error": "You are not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
    
    orders = Order.objects.filter(status='delivered', user=user)
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def cancelled_orders_client(request):
    user = request.user

    if not user.is_authenticated:
        return Response({"error": "You are not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
    
    orders = Order.objects.filter(status='cancelled', user=user)
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)



@api_view(['GET'])
def get_order(request, pk):
    order = get_object_or_404(Order, pk=pk)

    fast_shipping = 0
    if order.is_fast_shipping:
        fast_shipping = order.state.fast_shipping_price
    data = {
        "order": OrderSerializer(order).data,
        "total_price": order.total,
        "shipping_price": order.state.shipping_price,
        "fast_shipping": fast_shipping,
        "order_items": OrderItemSerializer(order.items.all(), many=True).data
    }
    return Response(data, status=status.HTTP_200_OK)

# @api_view(['PUT'])
# @authentication_classes([SessionAuthentication, TokenAuthentication])
# @permission_classes([IsAuthenticated])
# def update_order(request, pk):
#     order = get_object_or_404(Order, pk=pk)
#     data = request.data.copy()

#     serializer = OrderSerializer(order, data=data, partial=True)
#     if serializer.is_valid():
#         # Track order items from the request
#         order_items_data = data.get('order_items', [])
        
#         # Dictionary to track existing OrderItem objects
#         existing_items = {item.id: item for item in order.items.all()}
        
#         for item_data in order_items_data:
#             product_id = item_data.get('product')
#             quantity = item_data.get('quantity', 0)
            
#             try:
#                 # Check if the OrderItem already exists
#                 order_item = OrderItem.objects.get(order=order, product_id=product_id)
                
#                 # Update the quantity and check stock availability
#                 if int(quantity) > int(order_item.quantity):
#                     additional_quantity_needed = int(quantity) - int(order_item.quantity)
#                     if int(order_item.product.stock) < int(additional_quantity_needed):
#                         return Response({'error': f'Insufficient stock for product {order_item.product.name}'}, status=status.HTTP_400_BAD_REQUEST)
                    
#                     # Reduce stock
#                     order_item.product.stock -= additional_quantity_needed
#                 elif int(quantity) < int(order_item.quantity):
#                     # Increase stock back if the new quantity is less
#                     stock_difference = int(order_item.quantity) - int(quantity)
#                     order_item.product.stock += int(stock_difference)
                
#                 # Update the order item quantity
#                 order_item.quantity = int(quantity)
#                 order_item.save()
#                 order_item.product.save()
#                 existing_items.pop(order_item.id, None)  # Remove from existing items tracker
                
#             except OrderItem.DoesNotExist:
#                 # Handle new OrderItem creation
#                 product = get_object_or_404(Product, pk=product_id)
                
#                 if int(product.stock) < int(quantity):
#                     return Response({'error': f'Insufficient stock for product {product.name}'}, status=status.HTTP_400_BAD_REQUEST)
                
#                 # Create new OrderItem and reduce stock
#                 OrderItem.objects.create(order=order, product=product, quantity=quantity)
#                 product.stock -= int(quantity)
#                 product.save()
        
#         # Delete any OrderItems that are not included in the request data
#         for remaining_item in existing_items.values():
#             remaining_item.product.stock += remaining_item.quantity  # Restore stock
#             remaining_item.product.save()
#             remaining_item.delete()
        
#         # Save the order after processing items
#         order = serializer.save()
#         return Response(serializer.data, status=status.HTTP_200_OK)
    
#     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
@api_view(['PUT'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    data = request.data.copy()

    send_shipped_email = False
    if data.get('status') == 'shipped' and order.status != 'shipped':
        send_shipped_email = True

    send_delivered_email = False
    if data.get('status') == 'delivered' and order.status != 'delivered':
        send_delivered_email = True


    # Update order fields (except order_items)
    serializer = OrderSerializer(order, data=data, partial=True)
    if serializer.is_valid():
        # Process order_items only if they are included in the request
        order_items_data = data.get('order_items')
        if order_items_data is not None:
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

        # Save the order after processing items (if any)
        order = serializer.save()

        # i want to check if the status data that comes from request is !== to the current status of the order and if it is then i want to send an email to the user
        if order.status == 'delivered' and order.email and order.tracking_code and send_delivered_email:
            send_email(
                recipient_email=order.email,
                subject="تم تسليم شحنتك",
                message=f"""
                    <h2>تم تسليم شحنتك</h2>
                    <p style="margin-top: 15px">
                        تم تسليم الشحنة للمندوب وترقب وصولها اليوم من الساعة 9 صباحا حتى الساعة 9 مساءً
                    </p>
                    <p style="margin-top: 10px">
                        يمكنك تتبع الطلب من خلال هذا الكود {order.tracking_code}, من خلال <a href={front_end_url + '/orders/track/'}>هذه الصفحة</a>
                    </p>
                """,
                content_type="html"
            )
            print('email sent', order.email)

        if order.status == 'shipped' and order.email and order.tracking_code and send_shipped_email:
            send_email(
                recipient_email=order.email,
                subject="تم شحن طلبك",
                message=f"""
                    <h2>تم تغيير حالة الطلب وسيتم توصيلة قريبا</h2>
                    <p style="margin-top: 15px">
                        تم شحن طلبك, ترقب مكالمة المندوب في اي وقت قريب
                    </p>
                    <p style="margin-top: 10px">
                        يمكنك تتبع الطلب من خلال هذا الكود {order.tracking_code}, من خلال <a href=${front_end_url + '/orders/track/'}>هذه الصفحة</a>
                    </p>
                """,
                content_type="html"
            )
            print('email sent', order.email)
        

        # calculate total order
        order_items = order.items.all()
        order_total = 0
        for item in order_items:
            if item.product.offer_price:
                order_total += item.product.offer_price * item.quantity
            else:
                order_total += item.product.price * item.quantity
            
        order_total += order.state.shipping_price

        if order.is_fast_shipping:
            order_total += int(order.state.fast_shipping_price)

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



from django.db.models import F, Q


@api_view(['POST'])
def send_email_to_sales_with_his_target(request):
    date_from = request.data.get('date_from')
    date_to = request.data.get('date_to')

    user = CustomUser.objects.get(id=request.data['user_id'])

    orders = Order.objects.filter(
        Q(created_at__range=[date_from, date_to]) & 
        Q(sales_who_added__pk=user.pk) & 
        Q(status='delivered')
    ).order_by('-created_at')


    # get his total orders price
    orders_total_price = 0
    for order in orders:
        orders_total_price += order.total

    # user total commission
    user_commission = orders_total_price * (user.commission / 100)

    order_length = 0
    for order in orders:
        order_length += 1

    # send email to sales
    subject = 'Sales Report'
    message = f'''
        <h1>Sales Report</h1>
        <p>From: {date_from}</p>
        <p>To: {date_to}</p>
        <p>Total Orders: {order_length}</p>
        <p>Total Orders Price: {orders_total_price} EGP</p>
        <p>Your Total Commission: {user_commission} EGP</p>
    '''

    send_email(
        subject=subject,
        message=message,
        recipient_email=user.email,
        content_type="html",
    )

    return Response(status=status.HTTP_200_OK)




# cancel order
@api_view(['GET'])
def cancel_order(request):
    # Get order ID from the request
    order_id = request.GET.get('order_id')
    email = request.GET.get('email')

    if not order_id:
        return Response({"error": "Order ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Retrieve the order or return 404 if not found
    order = get_object_or_404(Order, id=order_id)

    if str(order.email) == str(email):
        # Check if the order was created in the last 24 hours
        cancellation_deadline = order.created_at + timedelta(days=1)

        if now() <= cancellation_deadline:
            order.status = 'cancelled'
            order.save()
            return Response(
                {"message": "Order cancelled successfully."}, 
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"message": "Cancellation period has expired. Order cannot be canceled."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        return Response({"error": "You have no permission to cancel this order."}, status=status.HTTP_400_BAD_REQUEST)





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

@api_view(['PUT'])
def update_home_page_image(request, pk):
    image = get_object_or_404(HomePageImage, pk=pk)
    serializer = HomePageImageSerializer(image, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def delete_home_page_image(request, pk):
    image = get_object_or_404(HomePageImage, pk=pk)
    image.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)





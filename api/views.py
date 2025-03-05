from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.response import Response
from rest_framework import status

from django.core.cache import cache


from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token

from .serializers import *
from .models import *

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


import random

@api_view(["POST"])
@permission_classes([AllowAny])
def register_verify_email(request):
    serializer = RegistrationSerializer(data=request.data)
    
    if CustomUser.objects.filter(email=serializer.initial_data.get("email")).exists():
        return Response({"email": ["هذا البريد الالكتروني مستخدم بالفعل"]}, status=status.HTTP_400_BAD_REQUEST)

    if serializer.is_valid():
        email = serializer.validated_data.get("email")
        # generate random 6 digit code
        code = str(random.randint(100000, 999999))
        
        # send email
        subject = "كود التحقق من حسابك"
        body = f"الكود هو {code} لا تشاركه مع احد."
        send_email(email, subject, body)

        cache.set(f"email_code_{email}", code, 60 * 60)
        
        return Response({"message": "Email verification code sent. Please enter the code."}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    """
    Register a new account (student or university) and return an auth token.
    """
    serializer = RegistrationSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data.get("email")
        code = cache.get(f"email_code_{email}")
        if str(code) != str(request.data.get("code")):
            return Response({"message": "Email verification code is incorrect"}, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)
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
    products = Product.objects.all().order_by('rank')

    if search:
        products = products.filter(name__icontains=search)

    if category:
        products = products.filter(category__id=category)

    if about_to_end:
        products = products.filter(Q(min_stock__isnull=False) & Q(stock__lte=F('min_stock')))

    serializer = ProductSerializer(products, many=True)
    return serializer.data
    # cache_key = "products_list"
    
    # if search:
    #     cache_key += f"_search{search}"
    # if category:
    #     cache_key += f"_category{category}"
    # if about_to_end:
    #     cache_key += f"_abouttoend{about_to_end}"
    
    # cached_products = cache.get(cache_key)
    
    # if not cached_products:
    #     print('Fetching products from database')
    #     products = Product.objects.all().order_by('rank')

    #     if search:
    #         products = products.filter(name__icontains=search)

    #     if category:
    #         products = products.filter(category__id=category)

    #     if about_to_end:
    #         products = products.filter(Q(min_stock__isnull=False) & Q(stock__lte=F('min_stock')))

    #     serializer = ProductSerializer(products, many=True)
    #     cached_products = serializer.data
    #     cache.set(cache_key, cached_products, timeout=CACHE_TIMEOUT)  # Cache the data
    # else:
    #     print('Fetching products from cache')

    # return cached_products

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

        # Get related products
        related_products_data = request.data.get('related_products_data', "")

        if isinstance(related_products_data, str):
            related_products_ids = list(map(int, filter(None, related_products_data.split(','))))
        else:
            related_products_ids = []

        # Update related products only if there's a change
        current_related_ids = set(product.related_products.values_list('id', flat=True))
        new_related_ids = set(related_products_ids)

        if current_related_ids != new_related_ids:
            product.related_products.set(Product.objects.filter(id__in=new_related_ids))

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
    users = CustomUser.objects.filter(Q(is_shipping_employee=True) | Q(is_fast_shipping_employee=True)).order_by('-id')
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)



from django.db.models import Q
from django.db.models import Sum, F


from hashlib import md5

def get_cached_orders(version=None, user=None, sales_id=None, search=None, status=None, fast_shipping=False, date_from=None, date_to=None, date=None, search_product=None):
    filters = Q()

    if date:
        filters &= Q(created_at__date__gte=now().date() - timedelta(days=int(date)))

    if search_product:
        filters &= Q(items__product__name__icontains=search_product)

    if date_from:
        filters &= Q(created_at__date__gte=date_from)

    if date_to:
        filters &= Q(created_at__date__lte=date_to)

    # if user and not (user.is_staff or user.is_superuser):
    #     filters &= Q(user=user)

    if sales_id:
        filters &= Q(sales_who_added__pk=sales_id)

    if search:
        search_fields = ['id', 'name', 'phone_number']
        search_filters = Q()
        for field in search_fields:
            search_filters |= Q(**{f"{field}__icontains": search})
        filters &= search_filters

    if status:
        filters &= Q(status=status)

    if fast_shipping:
        filters &= Q(is_fast_shipping=True)

    orders = Order.objects.filter(filters).order_by('-id').distinct()
    return orders


from datetime import datetime

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_orders(request):
    user = request.user

    sales_id = request.GET.get('sales_id', None)
    search = request.GET.get('search', None)
    status = request.GET.get('status', None)
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)

    fast_shipping_only = user.is_fast_shipping_employee

    # orders = get_cached_orders(version=None, user=user, sales_id=sales_id, search=search, status=status, fast_shipping=fast_shipping_only, date_from=date_from, date_to=date_to, date=None, search_product=None)
    orders = Order.objects.all().order_by('-id')

    if sales_id:
        orders = orders.filter(sales_who_added__pk=sales_id)

    if search:
        search_fields = ['id', 'name', 'phone_number']
        search_filters = Q()
        for field in search_fields:
            search_filters |= Q(**{f"{field}__icontains": search})
        orders = orders.filter(search_filters)

    if status:
        orders = orders.filter(status=status)

    if fast_shipping_only:
        orders = orders.filter(is_fast_shipping=True)

    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)

    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)

    orders_total_commission = 0
    total_orders_prices = sum(int(order.total) for order in orders if order.total)

    if sales_id and user.commission:
        for order in orders:
            if order.total:
                orders_total_commission += (int(order.total) * int(user.commission)) // 100

    data = {
        'orders': OrderSerializer(orders, many=True).data,
        'total_orders_prices': total_orders_prices,
        'total_commission': orders_total_commission,
    }

    return Response(data)



@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_customer_orders(request):
    user = request.user

    date = request.GET.get('date')
    search = request.GET.get('search')

    orders = get_cached_orders(user=user, date=date, search_product=search)

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








import datetime


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_home_for_admin(request):
    total_orders = Order.objects.count()
    out_of_stock = Product.objects.filter(stock=0).count()
    products = Product.objects.all().count()
    # get best seller
    
    sellers = CustomUser.objects.filter(Q(is_shipping_employee=True) | Q(is_fast_shipping_employee=True))
    best_seller = ''
    highest_commission = 0
    month = request.GET.get('month', None)
    year = request.GET.get('year', datetime.date.today().year)

    for seller in sellers:
        if month:
            orders = Order.objects.filter(
                sales_who_added=seller, 
                status='delivered', 
                created_at__year=year, 
                created_at__month=month
            )
        else:
            orders = Order.objects.filter(
                sales_who_added=seller, 
                status='delivered', 
                created_at__year=year
            )
        
        total_commission = sum(order.total * (seller.commission / 100) for order in orders if order.total)

        if total_commission > highest_commission:
            highest_commission = total_commission
            best_seller = str(seller.first_name) + ' ' + str(seller.last_name)
    

    data = {
        'total_orders': total_orders,
        'out_of_stock': out_of_stock,
        'products': products,
        'best_seller': best_seller
    }
    return Response(data)




from datetime import date
import calendar

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_total_orders_price_per_month(request):
    year = request.GET.get('year', date.today().year)

    # Get total orders per month in one optimized query
    orders_summary = (
        Order.objects.filter(created_at__year=year)
        .values('created_at__month')
        .annotate(total=Sum('total'))
    )

    # Initialize dictionary with month names and 0 as default value
    total_orders_price = {calendar.month_name[month]: 0 for month in range(1, 13)}

    # Fill in actual values from the database query
    for entry in orders_summary:
        month_name = calendar.month_name[entry['created_at__month']]
        total_orders_price[month_name] = entry['total']

    return Response(total_orders_price)


# response
# {
#     "January": 5000,
#     "February": 7000,
#     "March": 9000,
#     "April": 0,
#     "May": 0,
#     "June": 0,
#     "July": 0,
#     "August": 0,
#     "September": 0,
#     "October": 0,
#     "November": 0,
#     "December": 0
# }



@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_fast_shipping_and_shipping_employees(request):
    print('get_fast_shipping_and_shipping_employees')
    users = CustomUser.objects.filter(Q(is_fast_shipping_employee=True) | Q(is_shipping_employee=True))
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)











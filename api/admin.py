from django.contrib import admin
from .models import *

from django.utils.timezone import localtime

from rangefilter.filters import (
    DateRangeQuickSelectListFilterBuilder,
)



import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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



class CustomAdminSite(admin.AdminSite):
    def get_app_list(self, request):
        app_list = super().get_app_list(request)

        ordering = ['المحافظات', 'الأصناف', 'المنتجات', 'الطلبات', 'المستخدمين', 'الصفحة الرئيسية']
        
        for app in app_list:
            app['models'].sort(key=lambda x: ordering.index(x['name']) if x['name'] in ordering else 100)

        return app_list

admin_site = CustomAdminSite(name='myadmin')

admin_site.register(Category)



class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'rank', 'name', 'category', 'price', 'offer_price', 'stock', 'min_stock', 'created_at')
    list_editable = ('rank', 'name', 'price', 'offer_price', 'stock', 'min_stock')

admin_site.register(Product, ProductAdmin)


admin_site.register(State)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


class SellersFilter(admin.SimpleListFilter):
    title = 'Sellers'
    parameter_name = 'sellers'

    def lookups(self, request, model_admin):
        users = CustomUser.objects.filter(is_shipping_employee=True) | CustomUser.objects.filter(is_fast_shipping_employee=True)
        return [(user.id, str(user)) for user in users]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(sales_who_added=self.value())
        return queryset

class OrderAdmin(admin.ModelAdmin):
    change_list_template = "admin/api/order/change_list.html"
    
    inlines = [OrderItemInline]
    list_editable = ('status',)
    list_filter = ('is_fast_shipping', 'status', SellersFilter, ("created_at", DateRangeQuickSelectListFilterBuilder()))

    @admin.display(description="Sellers")
    def sellers(self, obj):
        users = obj.sales_who_added.all()
        filtered_users = users.filter(is_shipping_employee=True) | users.filter(is_fast_shipping_employee=True)
        if filtered_users.exists():
            return ", ".join([str(user) for user in filtered_users])
        return "-"

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return super().get_list_filter(request)
        else:
            return ['is_fast_shipping', 'status', ("created_at", DateRangeQuickSelectListFilterBuilder())]

    search_fields = ['id', 'tracking_code', 'name__icontains', 'phone_number']

    list_display = ('id', 'name', 'is_fast_shipping', 'status', 'total', 'created_at_formatted')

    fieldsets = ()

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)  # Get all fields automatically

        if request.user.is_fast_shipping_employee:
            excluded_fields = ['tracking_code', 'sales_who_added']  # Add the fields you want to exclude
            return [field for field in fields if field not in excluded_fields]

        if request.user.is_shipping_employee:
            excluded_fields = ['sales_who_added']  # Add the fields you want to exclude
            return [field for field in fields if field not in excluded_fields]

        return fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_fast_shipping_employee:
            qs = qs.filter(is_fast_shipping=True)

        search_term = request.GET.get('q')
        if search_term:
            qs = qs.filter(
                Q(id__icontains=search_term) |
                Q(tracking_code__icontains=search_term) |
                Q(name__icontains=search_term) |
                Q(phone_number__icontains=search_term)
            )

        filter_items = [
            {'param_name': 'is_fast_shipping__exact', 'model_field_name': 'is_fast_shipping'},
            {'param_name': 'status__exact', 'model_field_name': 'status'},
            {'param_name': 'sellers', 'model_field_name': 'sales_who_added__id'},
            {'param_name': 'created_at__gte', 'model_field_name': 'created_at__gte'},
            {'param_name': 'created_at__lte', 'model_field_name': 'created_at__lte'},
        ]

        for item in filter_items:
            param_value = request.GET.get(item['param_name'])
            if param_value:
                qs = qs.filter(**{item['model_field_name']: param_value})


        created_at_gte = request.GET.get('created_at__range__gte')
        created_at_lte = request.GET.get('created_at__range__lte')

        if created_at_gte and created_at_lte:
            qs = qs.filter(created_at__range=[created_at_gte, created_at_lte])
        elif created_at_gte:
            qs = qs.filter(created_at__gte=created_at_gte)
        elif created_at_lte:
            qs = qs.filter(created_at__lte=created_at_lte)

                
        return qs

    @admin.display(description='Created At')
    def created_at_formatted(self, obj):
        if obj.created_at:
            return localtime(obj.created_at).strftime("%Y-%m-%d %I:%M %p")
        return "-"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        queryset = self.get_queryset(request)

        # Orders count
        extra_context['total_orders'] = queryset.count()

        # Commission
        comm = float(0)
        sellers = request.GET.get('sellers')
        if sellers:
            user = CustomUser.objects.filter(id=sellers).first()
            if user:
                for order in queryset:
                    comm += float((order.total or 0) * (user.commission / 100))
        extra_context['total_commissions'] = comm

        # Total sales
        extra_context['total_sales'] = sum(float(order.total or 0) for order in queryset)
        
        return super().changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        obj.req_user = request.user
        super().save_model(request, obj, form, change)




admin_site.register(Order, OrderAdmin)





from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.contrib.admin.helpers import ActionForm
from django.contrib import messages
from django.db.models import Q

class DateRangeActionForm(ActionForm):
    start_date = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email']
    actions = ['send_emails']
    action_form = DateRangeActionForm  # Add Custom Form to Admin Actions

    def send_emails(self, request, queryset):
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        if not start_date or not end_date:
            self.message_user(request, "Please select both start and end dates", level=messages.ERROR)
            return

        # send email
        for user in queryset:
            orders = Order.objects.filter(
                Q(created_at__range=[start_date, end_date]) & 
                Q(sales_who_added__pk=user.pk) & 
                Q(status='delivered')
            ).order_by('-created_at')


            # get his total orders price
            orders_total_price = 0
            for order in orders:
                orders_total_price += order.total

            # user total commission
            user_commission = orders_total_price * (user.commission or 0 / 100)

            order_length = 0
            for order in orders:
                order_length += 1

            # send email to sales
            subject = 'Sales Report'
            message = f'''
                <h1>Sales Report</h1>
                <p>From: {start_date}</p>
                <p>To: {end_date}</p>
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

        self.message_user(request, f"{queryset.count()} users selected. Dates: {start_date} -> {end_date}")

    send_emails.short_description = "Send Emails in Date Range"

admin_site.register(CustomUser, CustomUserAdmin)


admin_site.register(HomePageImage)

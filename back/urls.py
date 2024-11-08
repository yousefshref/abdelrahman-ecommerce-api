"""
URL configuration for back project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from api import views

from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),

    path('register/', views.signup),
    path('login/', views.login),

    path('user/', views.user),
    path('users/', views.get_users),
    path('users/<int:pk>/update/', views.update_user),

    path('users/sales/', views.get_sales_users),

    path('categories/', views.get_categories),
    path('categories/create/', views.create_category),
    path('categories/update/<int:pk>/', views.update_category),
    path('categories/delete/<int:pk>/', views.delete_category),
    

    path('products/', views.get_products),
    path('products/<int:pk>/', views.get_product),
    path('products/update/<int:pk>/', views.update_product),
    path('products/create/', views.create_product),
    path('products/delete/<int:pk>/', views.delete_product),

    
    path('states/', views.states),

    path('orders/create/', views.create_order),
    path('orders/', views.get_orders),
    path('orders/update/<int:pk>/', views.update_order),
    path('orders/delete/<int:pk>/', views.delete_order),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
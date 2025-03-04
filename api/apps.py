from django.apps import AppConfig

class YourAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        from django.contrib import admin
        admin.site._registry = dict(sorted(admin.site._registry.items(), key=lambda x: [
            'category', 
            'product', 
            'state', 
            'order', 
            'customuser', 
            'homepageimage'
        ].index(x[0].__name__.lower()) if x[0].__name__.lower() in [
            'category', 
            'product', 
            'state', 
            'order', 
            'customuser', 
            'homepageimage'
        ] else 100))

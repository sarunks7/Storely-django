from django.contrib import admin
from .models import Product   

class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price', 'stock', 'is_available', 'category', 'created_date', 'updated_at')
    prepopulated_fields = {'slug': ('product_name',)}
   
admin.site.register(Product, ProductAdmin)
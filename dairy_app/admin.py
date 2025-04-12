from django.contrib import admin
from .models import MilkType, Customer, Sale, Payment

@admin.register(MilkType)
class MilkTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'rate_per_liter')
    search_fields = ('name',)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'address', 'date_joined')
    search_fields = ('name', 'phone')
    filter_horizontal = ('milk_types',)
    list_filter = ('date_joined',)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('customer', 'milk_type', 'quantity', 'rate', 'date', 'total_amount')
    list_filter = ('date', 'milk_type', 'customer')
    date_hierarchy = 'date'
    search_fields = ('customer__name', 'milk_type__name')
    
    def total_amount(self, obj):
        return f"₹{obj.quantity * obj.rate}"
    total_amount.short_description = "Total Amount"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'amount', 'date', 'description')
    list_filter = ('date', 'customer')
    date_hierarchy = 'date'
    search_fields = ('customer__name', 'description')

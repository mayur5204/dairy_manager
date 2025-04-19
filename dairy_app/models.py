from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum, F
from django.utils.translation import gettext_lazy as _

class MilkType(models.Model):
    """Model representing different types of milk (e.g., Cow, Buffalo)."""
    name = models.CharField(max_length=100)
    rate_per_liter = models.DecimalField(max_digits=10, decimal_places=2, help_text=_('Rate in Rs per liter'))
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        from django.utils.translation import gettext_lazy as _
        return f"{self.name} ({_('₹{rate}/liter').format(rate=self.rate_per_liter)})"


class Customer(models.Model):
    """Model representing a customer."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    milk_types = models.ManyToManyField(MilkType, related_name='customers')
    date_joined = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_balance(self):
        """Calculate the customer's current balance (sales minus payments)."""
        total_sales = Sale.objects.filter(customer=self).aggregate(
            total=Sum(F('quantity') * F('rate'), output_field=models.DecimalField())
        )['total'] or 0
        total_payments = Payment.objects.filter(customer=self).aggregate(
            total=Sum('amount')
        )['total'] or 0
        return total_sales - total_payments


class Sale(models.Model):
    """Model representing a milk sale/delivery."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sales')
    milk_type = models.ForeignKey(MilkType, on_delete=models.CASCADE, related_name='sales')
    date = models.DateField(default=timezone.now)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text='Quantity in liters')
    rate = models.DecimalField(max_digits=10, decimal_places=2, help_text='Rate in Rs per liter')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', 'customer__name']
        
    def __str__(self):
        return f"{self.customer.name} - {self.milk_type.name} - {self.date}"
    
    def total_amount(self):
        """Calculate the total amount for this sale."""
        return self.quantity * self.rate
    
    def save(self, *args, **kwargs):
        """Override the save method to set the rate from milk_type if not provided."""
        if not self.rate:
            self.rate = self.milk_type.rate_per_liter
        super().save(*args, **kwargs)


class Payment(models.Model):
    """Model representing a payment received from a customer."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payments')
    date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.customer.name} - ₹{self.amount} - {self.date}"

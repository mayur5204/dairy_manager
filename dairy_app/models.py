from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum, F, Min, Max
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import datetime
from calendar import month_name
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

class Area(models.Model):
    """Model representing a delivery area or zone."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='areas')
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_customer_count(self):
        """Return the number of customers in this area."""
        return self.customers.count()

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
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name='customers')
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
        
    def get_monthly_balances(self, update=False):
        """
        Get all monthly balance records for this customer.
        If update=True, recalculate all balances before returning.
        """
        if update:
            # This will update all monthly balances for the customer
            MonthlyBalance.update_monthly_balances(self)
            
        # Return all monthly balances for this customer
        return self.monthly_balances.all().order_by('-year', '-month')
    
    def get_pending_months(self):
        """
        Get a list of months for which the customer has unpaid balance.
        Returns a list of dictionaries with year, month, and balance information.
        Uses the MonthlyBalance model which properly tracks payment allocations.
        """
        # Update monthly balances first to ensure they're current
        MonthlyBalance.update_monthly_balances(self)
        
        # Get all monthly balances where is_paid is False and there are sales
        unpaid_balances = MonthlyBalance.objects.filter(
            customer=self,
            is_paid=False,
            sales_amount__gt=0  # Only include months with actual sales
        ).order_by('year', 'month')
        
        # Convert to the expected format
        pending_months = []
        for balance in unpaid_balances:
            import datetime
            current_date = datetime.date(balance.year, balance.month, 1)
            
            pending_months.append({
                'year': balance.year,
                'month': balance.month,
                'month_name': current_date.strftime('%B'),
                'balance': balance.sales_amount - balance.payment_amount,
                'sales': balance.sales_amount,
                'payments': balance.payment_amount,
            })
        
        return pending_months
        
    def get_month_payment_status(self, start_year, start_month, end_year=None, end_month=None):
        """
        Get the payment status for each month in a given range.
        If end_year and end_month are not provided, only checks the specified month.
        Returns a list of dictionaries with payment status for each month.
        """
        import datetime
        from calendar import month_name
        
        results = []
        
        # If end date not provided, check only the specific month
        if end_year is None or end_month is None:
            end_year, end_month = start_year, start_month
        
        # Create start and end dates
        current_date = datetime.date(start_year, start_month, 1)
        final_date = datetime.date(end_year, end_month, 1)
        
        while current_date <= final_date:
            year = current_date.year
            month = current_date.month
            
            # Get balance info for this month
            balance_info = self.get_month_balance(year, month)
            
            # Determine payment status
            if balance_info['sales_total'] == 0:
                status = 'no_sales'
            elif balance_info['month_balance'] <= 0:
                status = 'paid'
            else:
                status = 'pending'
            
            results.append({
                'year': year,
                'month': month,
                'month_name': month_name[month],
                'sales': balance_info['sales_total'],
                'payments': balance_info['payment_total'],
                'balance': balance_info['month_balance'],
                'status': status
            })
            
            # Move to next month
            if month == 12:
                current_date = datetime.date(year + 1, 1, 1)
            else:
                current_date = datetime.date(year, month + 1, 1)
        
        return results
    
    def get_month_balance(self, year, month):
        """
        Calculate the customer's balance for a specific month.
        Returns a dictionary with:
        - sales_total: Total sales for the specified month
        - payment_total: Total payments made for the specified month
        - month_balance: Balance for this month only (sales - payments)
        - previous_balance: Balance from all previous months
        - total_balance: Total balance including this month and all previous months
        """
        import datetime
        from decimal import Decimal
        
        # Generate start and end dates for the specified month
        start_date = datetime.date(year, month, 1)
        if month == 12:
            end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
            
        # Calculate sales for the specified month
        month_sales = Sale.objects.filter(
            customer=self,
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(
            total=Sum(F('quantity') * F('rate'), output_field=models.DecimalField())
        )['total'] or Decimal('0')
        
        # Calculate payments specifically assigned to this month
        month_payments = Payment.objects.filter(
            customer=self,
            payment_for_month=month,
            payment_for_year=year
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # Calculate sales and payments for all previous months
        previous_sales = Sale.objects.filter(
            customer=self,
            date__lt=start_date
        ).aggregate(
            total=Sum(F('quantity') * F('rate'), output_field=models.DecimalField())
        )['total'] or Decimal('0')
        
        # For previous payments, we need to account for:
        # 1. Payments made before this month that weren't assigned to any specific month
        # 2. Payments specifically assigned to months before this month
        prev_unassigned_payments = Payment.objects.filter(
            customer=self,
            date__lt=start_date,
            payment_for_month__isnull=True,
            payment_for_year__isnull=True
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        prev_assigned_payments = Payment.objects.filter(
            customer=self,
            payment_for_year__lt=year
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # Also include payments from this year but earlier months
        same_year_prev_months = Payment.objects.filter(
            customer=self,
            payment_for_year=year,
            payment_for_month__lt=month
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        previous_payments = prev_unassigned_payments + prev_assigned_payments + same_year_prev_months
        
        # Calculate balances
        month_balance = month_sales - month_payments
        previous_balance = previous_sales - previous_payments
        total_balance = previous_balance + month_balance
        
        return {
            'sales_total': month_sales,
            'payment_total': month_payments,
            'month_balance': month_balance,
            'previous_balance': previous_balance,
            'total_balance': total_balance,
            'start_date': start_date,
            'end_date': end_date
        }
    
    def get_last_six_months_status(self):
        """
        Get the monthly balance status for the last 6 months.
        Returns a list of dictionaries with month-wise balance information.
        """
        import datetime
        from calendar import month_name
        from decimal import Decimal
        
        # Update monthly balances first to ensure they're current
        MonthlyBalance.update_monthly_balances(self)
        
        # Get current date
        today = datetime.date.today()
        
        # Calculate start date (6 months ago)
        if today.month > 6:
            start_month = today.month - 6
            start_year = today.year
        else:
            start_month = today.month - 6 + 12
            start_year = today.year - 1
        
        # Generate list of last 6 months
        months_data = []
        current_month = start_month
        current_year = start_year
        
        for i in range(6):
            # Get or create monthly balance record
            try:
                monthly_balance = MonthlyBalance.objects.get(
                    customer=self,
                    year=current_year,
                    month=current_month
                )
                sales_amount = monthly_balance.sales_amount
                payment_amount = monthly_balance.payment_amount
                is_paid = monthly_balance.is_paid
                balance = sales_amount - payment_amount
            except MonthlyBalance.DoesNotExist:
                # If no record exists, calculate manually
                month_balance_info = self.get_month_balance(current_year, current_month)
                sales_amount = month_balance_info['sales_total']
                payment_amount = month_balance_info['payment_total']
                balance = month_balance_info['month_balance']
                is_paid = balance <= 0 and sales_amount > 0
            
            # Determine status
            if sales_amount == 0:
                status = 'no_sales'
                status_class = 'secondary'
                status_text = 'No Sales'
            elif is_paid or balance <= 0:
                status = 'paid'
                status_class = 'success'
                status_text = 'Paid'
            else:
                status = 'pending'
                status_class = 'danger'
                status_text = 'Pending'
            
            months_data.append({
                'year': current_year,
                'month': current_month,
                'month_name': month_name[current_month],
                'month_short': month_name[current_month][:3],
                'sales_amount': sales_amount,
                'payment_amount': payment_amount,
                'balance': balance,
                'status': status,
                'status_class': status_class,
                'status_text': status_text,
                'is_paid': is_paid
            })
            
            # Move to next month
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
        
        # Return in reverse order (most recent first)
        return list(reversed(months_data))


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
    # New fields to track which month this payment is for
    payment_for_month = models.IntegerField(null=True, blank=True, 
                                           help_text=_('Month number (1-12) this payment is for'))
    payment_for_year = models.IntegerField(null=True, blank=True,
                                          help_text=_('Year this payment is for'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        month_info = ""
        if self.payment_for_month and self.payment_for_year:
            from calendar import month_name
            month_info = f" (for {month_name[self.payment_for_month]} {self.payment_for_year})"
        return f"{self.customer.name} - ₹{self.amount} - {self.date}{month_info}"
    
    def save(self, *args, **kwargs):
        # Handle payment_for_month/year if they're not None
        # (they should be None for multi-month payments)
        if not self.payment_for_month and self.payment_for_month is not None:
            self.payment_for_month = self.date.month
        if not self.payment_for_year and self.payment_for_year is not None:
            self.payment_for_year = self.date.year
        
        # Save the payment first
        super().save(*args, **kwargs)
        
        # Update allocations will be handled separately by the view
        # to support distributing a payment across multiple months
        
        # Only update the monthly balance for the specified month if it's a single-month payment
        if self.payment_for_month is not None and self.payment_for_year is not None:
            # Update the monthly balance record
            MonthlyBalance.update_monthly_balances(
                self.customer, 
                year=self.payment_for_year, 
                month=self.payment_for_month
            )
            
    def distribute_to_months(self, month_allocations=None):
        """
        Distribute this payment across multiple months.
        
        Args:
            month_allocations: List of dicts with keys 'month', 'year', and 'amount'
                              If not provided, will use payment_for_month/year to create a single allocation
        
        Returns:
            List of created PaymentAllocation objects
        """
        from django.db import transaction
        from decimal import Decimal
        from django.apps import apps
        
        # Get the PaymentAllocation model to avoid forward reference issues
        PaymentAllocation = apps.get_model('dairy_app', 'PaymentAllocation')
        
        # If no specific allocations are provided, create one based on payment_for_month/year
        if not month_allocations:
            if not self.payment_for_month or not self.payment_for_year:
                return []
                
            month_allocations = [{
                'month': self.payment_for_month,
                'year': self.payment_for_year,
                'amount': self.amount
            }]
        
        # Validate total amount doesn't exceed payment amount
        total_allocated = sum(Decimal(str(alloc.get('amount', 0))) for alloc in month_allocations)
        if total_allocated > self.amount:
            raise ValueError("Total allocated amount exceeds payment amount")
        
        # Process allocations within a transaction
        with transaction.atomic():
            # Delete existing allocations
            PaymentAllocation.objects.filter(payment=self).delete()
            
            # Create new allocations
            created_allocations = []
            months_to_update = set()
            
            for alloc in month_allocations:
                allocation = PaymentAllocation.objects.create(
                    payment=self,
                    month=alloc['month'],
                    year=alloc['year'],
                    amount=alloc['amount']
                )
                created_allocations.append(allocation)
                
                # Track which months need updating
                months_to_update.add((alloc['year'], alloc['month']))
            
            # Update all affected monthly balances after creating all allocations
            for year, month in months_to_update:
                MonthlyBalance.update_monthly_balances(
                    self.customer,
                    year=year,
                    month=month
                )
                
            return created_allocations


class MonthlyBalance(models.Model):
    """Model representing a monthly balance calculation for a customer."""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='monthly_balances')
    year = models.IntegerField()
    month = models.IntegerField(help_text=_('Month number (1-12)'))
    sales_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    last_calculated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-year', '-month']
        unique_together = ['customer', 'year', 'month']
    
    def __str__(self):
        from calendar import month_name
        status = "Paid" if self.is_paid else "Pending"
        return f"{self.customer.name} - {month_name[self.month]} {self.year} - {status}"
    
    def recalculate(self):
        """Recalculate the monthly balance based on sales and payments."""
        from decimal import Decimal
        import datetime
        
        # Generate start and end dates for the month
        start_date = datetime.date(self.year, self.month, 1)
        if self.month == 12:
            end_date = datetime.date(self.year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.date(self.year, self.month + 1, 1) - datetime.timedelta(days=1)
        
        # Calculate sales for this month
        month_sales = Sale.objects.filter(
            customer=self.customer,
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(
            total=Sum(F('quantity') * F('rate'), output_field=models.DecimalField())
        )['total'] or Decimal('0')
        
        # Calculate payments specifically assigned to this month
        # This includes:
        # 1. Payments with matching payment_for_month/year OR
        # 2. Payments made during this month if payment_for_month/year isn't specified
        # 3. Payments with allocations for this month/year
        
        # Get payments directly assigned to this month
        direct_payments = Payment.objects.filter(
            customer=self.customer,
            payment_for_month=self.month,
            payment_for_year=self.year
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # Get payment allocations for this month
        from django.apps import apps
        try:
            PaymentAllocation = apps.get_model('dairy_app', 'PaymentAllocation')
            
            # Get all payment allocations for this month and year
            allocations = PaymentAllocation.objects.filter(
                payment__customer=self.customer,
                month=self.month,
                year=self.year
            )
            
            # Force evaluation to make sure we have the latest data
            allocations = list(allocations)
            
            allocated_payments = sum(alloc.amount for alloc in allocations) if allocations else Decimal('0')
        except ImportError:
            # PaymentAllocation model may not be available yet (during migrations)
            allocated_payments = Decimal('0')
        
        # Total payments is the sum of direct and allocated payments
        month_payments = direct_payments + allocated_payments
        
        # Update fields
        self.sales_amount = month_sales
        self.payment_amount = month_payments
        
        # A month is considered paid when payment amount equals or exceeds sales amount
        # Using Decimal for precise comparison
        from decimal import Decimal
        self.is_paid = self.payment_amount >= self.sales_amount
        
        self.save()
        
        return {
            'sales': self.sales_amount,
            'payments': self.payment_amount,
            'balance': self.sales_amount - self.payment_amount,
            'is_paid': self.is_paid
        }
    
    @classmethod
    def update_monthly_balances(cls, customer, year=None, month=None):
        """
        Update or create monthly balance records for a customer.
        If year and month are specified, update only that month.
        Otherwise, update all months with sales activity.
        """
        import datetime
        from django.db.models import Min, Max
        
        # If specific month requested
        if year and month:
            # Get or create the monthly balance record
            balance, created = cls.objects.get_or_create(
                customer=customer,
                year=year,
                month=month
            )
            return balance.recalculate()
        
        # Otherwise update all months with activity
        date_range = Sale.objects.filter(customer=customer).aggregate(
            earliest=Min('date'),
            latest=Max('date')
        )
        
        if not date_range['earliest'] or not date_range['latest']:
            return []
            
        # Create a list to store results
        results = []
        
        # Start from the first month
        current_date = datetime.date(date_range['earliest'].year, date_range['earliest'].month, 1)
        end_date = datetime.date(date_range['latest'].year, date_range['latest'].month, 1)
        
        # Loop through each month
        while current_date <= end_date:
            year = current_date.year
            month = current_date.month
            
            # Get or create the monthly balance record
            balance, created = cls.objects.get_or_create(
                customer=customer,
                year=year,
                month=month
            )
            
            # Update it and store the result
            result = balance.recalculate()
            result.update({'year': year, 'month': month})
            results.append(result)
            
            # Move to the next month
            if month == 12:
                current_date = datetime.date(year + 1, 1, 1)
            else:
                current_date = datetime.date(year, month + 1, 1)
        
        return results


class PaymentAllocation(models.Model):
    """Model to track how a payment is allocated across multiple months."""
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='allocations')
    month = models.IntegerField(help_text=_('Month number (1-12)'))
    year = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-year', '-month']
        unique_together = ['payment', 'year', 'month']
        
    def __str__(self):
        from calendar import month_name
        return f"{self.payment.customer.name} - {month_name[self.month]} {self.year} - ₹{self.amount}"

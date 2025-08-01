from django import forms
from django.contrib.auth.models import User
from .models import MilkType, Customer, Sale, Payment, Area, MonthlyBalance
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import datetime


class AreaForm(forms.ModelForm):
    """Form for creating and updating delivery areas."""
    class Meta:
        model = Area
        fields = ['name', 'description']
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Ensure labels can be translated
        from django.utils.translation import gettext_lazy as _
        self.fields['name'].label = _('Area Name*')
        self.fields['description'].label = _('Description')
        
    def save(self, commit=True):
        area = super().save(commit=False)
        if self.user and not area.pk:  # Only set user on new area creation
            area.user = self.user
        if commit:
            area.save()
        return area

class MilkTypeForm(forms.ModelForm):
    """Form for creating and updating milk types."""
    class Meta:
        model = MilkType
        fields = ['name', 'rate_per_liter']
        widgets = {
            'rate_per_liter': forms.NumberInput(attrs={'min': '0', 'step': '0.01'})
        }
    
    def clean_rate_per_liter(self):
        from django.utils.translation import gettext_lazy as _
        
        rate = self.cleaned_data.get('rate_per_liter')
        if rate <= 0:
            raise ValidationError(_("Rate must be greater than zero."))
        return rate
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure labels can be translated
        from django.utils.translation import gettext_lazy as _
        self.fields['name'].label = _('Name')
        self.fields['rate_per_liter'].label = _('Rate per liter (₹)')


class CustomerForm(forms.ModelForm):
    """Form for creating and updating customers."""
    class Meta:
        model = Customer
        fields = ['name', 'address', 'phone', 'area', 'milk_types']
        widgets = {
            'milk_types': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Show areas based on user permissions - all areas for superusers, only own areas for regular users
        if self.user:
            if self.user.is_superuser:
                self.fields['area'].queryset = Area.objects.all()
            else:
                self.fields['area'].queryset = Area.objects.filter(user=self.user)
        
        # Ensure labels can be translated
        from django.utils.translation import gettext_lazy as _
        self.fields['name'].label = _('Name*')
        self.fields['address'].label = _('Address')
        self.fields['phone'].label = _('Phone')
        self.fields['area'].label = _('Delivery Area')
        self.fields['milk_types'].label = _('Milk Types*')


class SaleForm(forms.ModelForm):
    """Form for recording milk sales."""
    class Meta:
        model = Sale
        fields = ['customer', 'milk_type', 'date', 'quantity', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'quantity': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
        }
        labels = {
            'date': 'Date*',  # Label will be translated via django.po file
        }
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        return quantity
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        customer_fixed = kwargs.pop('customer_fixed', False)
        super().__init__(*args, **kwargs)
        
        # If customer is fixed (coming from customer page), hide the customer field
        if customer_fixed:
            self.fields['customer'].widget = forms.HiddenInput()
        else:
            # Show all customers
            self.fields['customer'].queryset = Customer.objects.all()
        
        # Show all milk types instead of filtering by customer
        self.fields['milk_type'].queryset = MilkType.objects.all()
        
        # Ensure labels can be translated
        from django.utils.translation import gettext_lazy as _
        self.fields['date'].label = _('Date*')
        self.fields['customer'].label = _('Customer')
        self.fields['milk_type'].label = _('Milk Type')
        self.fields['quantity'].label = _('Quantity')
        self.fields['notes'].label = _('Notes')


class SaleInputForm(forms.Form):
    """Form for batch input of milk sales (format: e.g., '1-2-B' for 1 liter Cow and 2 liters Buffalo)."""
    customer = forms.ModelChoiceField(queryset=Customer.objects.all())
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    sales_input = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'e.g., 1-2-B for 1 liter Cow and 2 liters Buffalo'}),
        help_text="Format: [quantity]-[quantity]-[first letter of milk type]. Example: 1-2-B for 1 liter Cow and 2 liters Buffalo"
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Keep for backward compatibility but don't use it
        super().__init__(*args, **kwargs)
        # Show all customers regardless of user
        self.fields['customer'].queryset = Customer.objects.all()
    
    def clean(self):
        cleaned_data = super().clean()
        sales_input = cleaned_data.get('sales_input')
        customer = cleaned_data.get('customer')
        
        if sales_input and customer:
            # Get milk types assigned to this customer
            customer_milk_types = customer.milk_types.all()
            customer_codes = {milk_type.name[0].upper(): milk_type for milk_type in customer_milk_types}
            
            if not customer_codes:
                raise ValidationError("Selected customer has no milk types assigned.")
            
            parts = sales_input.split('-')
            if len(parts) >= 3:
                type_codes = list(parts[-1].upper())
                
                for type_code in type_codes:
                    if type_code not in customer_codes:
                        available_codes = ', '.join(customer_codes.keys())
                        milk_type_names = ', '.join(mt.name for mt in customer_milk_types)
                        raise ValidationError(
                            f"Invalid milk type code '{type_code}' for this customer. "
                            f"Available codes for {customer.name}: {available_codes} ({milk_type_names})"
                        )
        
        return cleaned_data


class PaymentForm(forms.ModelForm):
    """Form for recording payments from customers."""
    is_multi_month = forms.BooleanField(
        required=False, 
        label=_("Distribute across multiple months"),
        help_text=_("Enable to distribute this payment across multiple unpaid months")
    )
    
    class Meta:
        model = Payment
        fields = ['customer', 'date', 'amount', 'payment_for_month', 'payment_for_year', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'amount': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'payment_for_month': forms.Select(choices=[
                (i, datetime.date(2000, i, 1).strftime('%B')) for i in range(1, 13)
            ]),
            'payment_for_year': forms.Select(choices=[
                (y, y) for y in range(datetime.datetime.now().year - 5, datetime.datetime.now().year + 1)
            ]),
        }
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        return amount
        
    def clean(self):
        """Ensure payment_for_month/year fields are handled correctly with multi-month allocation."""
        cleaned_data = super().clean()
        
        # If multi-month is selected, set payment_for_month/year to None to avoid confusion
        if cleaned_data.get('is_multi_month'):
            cleaned_data['payment_for_month'] = None
            cleaned_data['payment_for_year'] = None
            
        return cleaned_data
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Keep for backward compatibility but don't use it
        customer_fixed = kwargs.pop('customer_fixed', False)
        super().__init__(*args, **kwargs)
        
        # If customer is fixed (coming from customer page), hide the customer field
        if customer_fixed:
            self.fields['customer'].widget = forms.HiddenInput()
        else:
            # Show all customers regardless of user
            self.fields['customer'].queryset = Customer.objects.all()
        
        # Ensure labels can be translated
        self.fields['date'].label = _('Date*')
        self.fields['amount'].label = _('Amount*')
        self.fields['description'].label = _('Description')
        self.fields['customer'].label = _('Customer')
        self.fields['payment_for_month'].label = _('Payment for Month')
        self.fields['payment_for_year'].label = _('Payment for Year')
        
        # Default to current month and year if creating a new payment
        # and not using multi-month mode
        if not self.instance.pk:
            # Check if multi-month is set in POST data
            is_multi_month = False
            if self.data and 'is_multi_month' in self.data:
                is_multi_month = self.data.get('is_multi_month') == 'on'
                
            if not is_multi_month:
                self.fields['payment_for_month'].initial = datetime.datetime.now().month
                self.fields['payment_for_year'].initial = datetime.datetime.now().year
        
        # Helpful text
        self.fields['payment_for_month'].help_text = _('Select which month this payment applies to')
        self.fields['payment_for_year'].help_text = _('Select which year this payment applies to')
        
        # Store unpaid months for the selected customer
        self.unpaid_months = []
        if 'customer' in self.data:
            try:
                customer_id = int(self.data.get('customer'))
                customer = Customer.objects.get(id=customer_id)
                self.unpaid_months = self.get_unpaid_months(customer)
            except (ValueError, Customer.DoesNotExist):
                pass
        elif self.instance.pk:
            self.unpaid_months = self.get_unpaid_months(self.instance.customer)
    
    def get_unpaid_months(self, customer):
        """Get a list of unpaid months for the customer."""
        from django.db.models import F
        
        # Get all monthly balances that are not paid
        # Force recalculation first to ensure we have the latest data
        MonthlyBalance.update_monthly_balances(customer)
        
        unpaid_balances = MonthlyBalance.objects.filter(
            customer=customer,
            is_paid=False,
            sales_amount__gt=0
        ).order_by('-year', '-month')
        
        # Calculate remaining amount for each month
        result = []
        for balance in unpaid_balances:
            month_data = {
                'month': balance.month,
                'year': balance.year,
                'sales_amount': balance.sales_amount,
                'payment_amount': balance.payment_amount,
                'remaining': balance.sales_amount - balance.payment_amount,
            }
            
            from calendar import month_name
            month_data['month_name'] = month_name[balance.month]
            
            result.append(month_data)
            
        return result
from django import forms
from django.contrib.auth.models import User
from .models import MilkType, Customer, Sale, Payment
from django.core.exceptions import ValidationError
import datetime


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
        fields = ['name', 'address', 'phone', 'milk_types']
        widgets = {
            'milk_types': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure labels can be translated
        from django.utils.translation import gettext_lazy as _
        self.fields['name'].label = _('Name*')
        self.fields['address'].label = _('Address')
        self.fields['phone'].label = _('Phone')
        self.fields['milk_types'].label = _('Milk Types*')


class SaleForm(forms.ModelForm):
    """Form for recording milk sales."""
    class Meta:
        model = Sale
        fields = ['customer', 'milk_type', 'date', 'quantity', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'quantity': forms.NumberInput(attrs={'min': '0', 'step': '0.1'}),
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
        super().__init__(*args, **kwargs)
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
    class Meta:
        model = Payment
        fields = ['customer', 'date', 'amount', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'amount': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
        }
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        return amount
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Keep for backward compatibility but don't use it
        super().__init__(*args, **kwargs)
        # Show all customers regardless of user
        self.fields['customer'].queryset = Customer.objects.all()
        
        # Ensure labels can be translated
        from django.utils.translation import gettext_lazy as _
        self.fields['date'].label = _('Date*')
        self.fields['amount'].label = _('Amount*')
        self.fields['description'].label = _('Description')
        self.fields['customer'].label = _('Customer')


class DateRangeForm(forms.Form):
    """Form for selecting date range for reports."""
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure labels can be translated
        from django.utils.translation import gettext_lazy as _
        self.fields['start_date'].label = _('Start Date*')
        self.fields['end_date'].label = _('End Date*')


class MonthSelectionForm(forms.Form):
    """Form for selecting month and year for monthly reports."""
    from django.utils.translation import gettext_lazy as _
    
    MONTH_CHOICES = [
        (1, _('January')), (2, _('February')), (3, _('March')),
        (4, _('April')), (5, _('May')), (6, _('June')),
        (7, _('July')), (8, _('August')), (9, _('September')),
        (10, _('October')), (11, _('November')), (12, _('December'))
    ]
    
    month = forms.ChoiceField(choices=MONTH_CHOICES)
    year = forms.ChoiceField()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dynamically generate year choices (current year and 2 years back)
        current_year = datetime.date.today().year
        year_choices = [(year, str(year)) for year in range(current_year - 2, current_year + 1)]
        self.fields['year'].choices = year_choices
        
        # Ensure labels can be translated
        from django.utils.translation import gettext_lazy as _
        self.fields['month'].label = _('Select Month')
        self.fields['year'].label = _('Select Year')
        
        # Add dropdown icon styling using Bootstrap classes
        self.fields['month'].widget.attrs.update({
            'class': 'form-select',
            'aria-label': _('Select Month')
        })
        self.fields['year'].widget.attrs.update({
            'class': 'form-select',
            'aria-label': _('Select Year')
        })
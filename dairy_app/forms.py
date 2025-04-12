from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import MilkType, Customer, Sale, Payment
from django.core.exceptions import ValidationError


class CustomUserCreationForm(UserCreationForm):
    """Custom user registration form with additional email field."""
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class MilkTypeForm(forms.ModelForm):
    """Form for creating and updating milk types."""
    class Meta:
        model = MilkType
        fields = ['name', 'rate_per_liter']
        widgets = {
            'rate_per_liter': forms.NumberInput(attrs={'min': '0', 'step': '0.01'})
        }
    
    def clean_rate_per_liter(self):
        rate = self.cleaned_data.get('rate_per_liter')
        if rate <= 0:
            raise ValidationError("Rate must be greater than zero.")
        return rate


class CustomerForm(forms.ModelForm):
    """Form for creating and updating customers."""
    class Meta:
        model = Customer
        fields = ['name', 'address', 'phone', 'milk_types']
        widgets = {
            'milk_types': forms.CheckboxSelectMultiple(),
        }


class SaleForm(forms.ModelForm):
    """Form for recording milk sales."""
    class Meta:
        model = Sale
        fields = ['customer', 'milk_type', 'date', 'quantity', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'quantity': forms.NumberInput(attrs={'min': '0', 'step': '0.1'}),
        }
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        return quantity
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Keep for backward compatibility but don't use it
        super().__init__(*args, **kwargs)
        # Show all customers
        self.fields['customer'].queryset = Customer.objects.all()
        # Show all milk types
        self.fields['milk_type'].queryset = MilkType.objects.all()


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
        
        # Get all available milk types
        all_milk_types = MilkType.objects.all()
        all_codes = {milk_type.name[0].upper(): milk_type for milk_type in all_milk_types}
        
        if sales_input:
            parts = sales_input.split('-')
            if len(parts) >= 3:
                type_codes = list(parts[-1].upper())
                
                for type_code in type_codes:
                    if type_code not in all_codes:
                        raise ValidationError(f"Milk type code '{type_code}' is not valid. "
                                            f"Available codes are: {', '.join(all_codes.keys())}.")
        
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


class DateRangeForm(forms.Form):
    """Form for selecting date range for reports."""
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
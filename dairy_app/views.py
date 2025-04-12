from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, JsonResponse

from .models import MilkType, Customer, Sale, Payment
from .forms import (
    CustomUserCreationForm, MilkTypeForm, CustomerForm, SaleForm, 
    SaleInputForm, PaymentForm, DateRangeForm
)

import re
from datetime import timedelta
from decimal import Decimal

# Authentication Views
def register_view(request):
    """View for user registration"""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created for {user.username}!")
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, "dairy_app/register.html", {"form": form})


@login_required
def dashboard_view(request):
    """Main dashboard view showing summary data"""
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    # Get customers count
    customers_count = Customer.objects.all().count()
    
    # Get today's sales
    today_sales = Sale.objects.filter(date=today)
    today_total_quantity = today_sales.aggregate(total=Sum('quantity'))['total'] or 0
    today_total_amount = today_sales.aggregate(
        total=Sum(F('quantity') * F('rate'), output_field=DecimalField())
    )['total'] or 0
    
    # Get month's sales
    month_sales = Sale.objects.filter(
        date__gte=start_of_month, 
        date__lte=today
    )
    month_total_amount = month_sales.aggregate(
        total=Sum(F('quantity') * F('rate'), output_field=DecimalField())
    )['total'] or 0
    
    # Get month's payments
    month_payments = Payment.objects.filter(
        date__gte=start_of_month, 
        date__lte=today
    )
    month_total_payment = month_payments.aggregate(total=Sum('amount'))['total'] or 0
    
    # Get recent sales
    recent_sales = Sale.objects.order_by('-date')[:5]
    
    # Get recent payments
    recent_payments = Payment.objects.order_by('-date')[:5]
    
    # Get milk type distribution for today
    milk_type_distribution = []
    milk_types = MilkType.objects.filter(sales__date=today).distinct()
    
    for milk_type in milk_types:
        type_sales = today_sales.filter(milk_type=milk_type)
        quantity = type_sales.aggregate(total=Sum('quantity'))['total'] or 0
        amount = type_sales.aggregate(
            total=Sum(F('quantity') * F('rate'), output_field=DecimalField())
        )['total'] or 0
        
        milk_type_distribution.append({
            'name': milk_type.name,
            'quantity': quantity,
            'amount': amount
        })
    
    context = {
        'customers_count': customers_count,
        'today_total_quantity': today_total_quantity,
        'today_total_amount': today_total_amount,
        'month_total_amount': month_total_amount,
        'month_total_payment': month_total_payment,
        'recent_sales': recent_sales,
        'recent_payments': recent_payments,
        'milk_type_distribution': milk_type_distribution,
        'today': today,
    }
    
    return render(request, 'dairy_app/dashboard.html', context)


# Milk Type Views
class MilkTypeListView(LoginRequiredMixin, ListView):
    model = MilkType
    template_name = 'dairy_app/milk_type_list.html'
    context_object_name = 'milk_types'
    
    def get_queryset(self):
        # Return all milk types since they could be shared across users
        return MilkType.objects.all()


class MilkTypeCreateView(LoginRequiredMixin, CreateView):
    model = MilkType
    form_class = MilkTypeForm
    template_name = 'dairy_app/milk_type_form.html'
    success_url = reverse_lazy('milk_type_list')
    
    def form_valid(self, form):
        messages.success(self.request, f"Milk type '{form.instance.name}' created successfully!")
        return super().form_valid(form)


class MilkTypeUpdateView(LoginRequiredMixin, UpdateView):
    model = MilkType
    form_class = MilkTypeForm
    template_name = 'dairy_app/milk_type_form.html'
    success_url = reverse_lazy('milk_type_list')
    
    def form_valid(self, form):
        messages.success(self.request, f"Milk type '{form.instance.name}' updated successfully!")
        return super().form_valid(form)


class MilkTypeDeleteView(LoginRequiredMixin, DeleteView):
    model = MilkType
    template_name = 'dairy_app/milk_type_confirm_delete.html'
    success_url = reverse_lazy('milk_type_list')
    
    def delete(self, request, *args, **kwargs):
        milk_type = self.get_object()
        messages.success(request, f"Milk type '{milk_type.name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)


# Customer Views
class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'dairy_app/customer_list.html'
    context_object_name = 'customers'
    
    def get_queryset(self):
        queryset = Customer.objects.all()
        search_query = self.request.GET.get('search', '').strip()
        
        if search_query:
            # More comprehensive search across name field
            queryset = queryset.filter(name__icontains=search_query)
            
        return queryset.order_by('name')  # Ensure consistent ordering
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current month data
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        
        customer_data = {}
        
        # Get all milk types for labeling
        all_milk_types = MilkType.objects.all()
        
        # Process each customer
        for customer in context['customers']:
            # Calculate monthly milk delivery by type
            milk_delivery = {}
            monthly_sales = Sale.objects.filter(
                customer=customer,
                date__gte=start_of_month,
                date__lte=today
            ).values('milk_type__name').annotate(
                total_quantity=Sum('quantity')
            )
            
            for sale in monthly_sales:
                milk_type_name = sale['milk_type__name']
                milk_delivery[milk_type_name] = sale['total_quantity']
            
            # Calculate balance
            total_sales = Sale.objects.filter(customer=customer).aggregate(
                total=Sum(F('quantity') * F('rate'), output_field=DecimalField())
            )['total'] or 0
            
            total_payments = Payment.objects.filter(customer=customer).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            balance = total_sales - total_payments
            
            customer_data[customer.id] = {
                'milk_delivery': milk_delivery,
                'balance': balance
            }
        
        context['customer_data'] = customer_data
        context['milk_types'] = all_milk_types
        context['search_query'] = self.request.GET.get('search', '')
        context['current_month'] = today.strftime('%B %Y')
        
        return context
        
    def get(self, request, *args, **kwargs):
        # Check if request is AJAX, but only consider it AJAX if the special custom parameter is set
        is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                  request.GET.get('ajax_search') == 'true')
        
        if is_ajax:
            # Use the normal queryset function to get filtered customers
            queryset = self.get_queryset()
            
            # Get context data for calculating milk delivery and balance
            context = self.get_context_data(object_list=queryset)
            customers_data = context['customers']
            customer_data = context['customer_data']
            
            # Return only what we need for the response
            html_content = []
            
            for idx, customer in enumerate(customers_data):
                # Format milk types
                milk_types_html = ""
                if customer.milk_types.exists():
                    for milk_type in customer.milk_types.all():
                        milk_types_html += f'<span class="badge bg-success">{milk_type.name}</span> '
                else:
                    milk_types_html = '<span class="badge bg-light text-dark">None</span>'
                
                # Format milk delivery
                delivery_html = ""
                if customer.id in customer_data and customer_data[customer.id]['milk_delivery']:
                    for milk_type_name, quantity in customer_data[customer.id]['milk_delivery'].items():
                        delivery_html += f'<span class="badge bg-info text-dark">{milk_type_name}: {quantity:.1f} L</span> '
                else:
                    delivery_html = '<span class="badge bg-light text-dark">No deliveries</span>'
                
                # Format balance
                balance = customer_data[customer.id]['balance']
                balance_class = "bg-success" if balance > 0 else "bg-danger" if balance < 0 else "bg-light text-dark"
                balance_html = f'<span class="badge {balance_class} fs-6">₹{balance:.2f}</span>'
                
                # Create row
                row = {
                    'counter': idx + 1,
                    'id': customer.id,
                    'name': customer.name,
                    'milk_types_html': milk_types_html,
                    'delivery_html': delivery_html,
                    'balance_html': balance_html
                }
                
                html_content.append(row)
            
            # Return JSON response
            return JsonResponse({'customers': html_content})
            
        # Regular request - proceed as normal
        return super().get(request, *args, **kwargs)


class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'dairy_app/customer_detail.html'
    context_object_name = 'customer'
    
    def get_queryset(self):
        # Return all customers
        return Customer.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object
        
        # Get recent sales
        context['recent_sales'] = Sale.objects.filter(customer=customer).order_by('-date')[:10]
        
        # Get recent payments
        context['recent_payments'] = Payment.objects.filter(customer=customer).order_by('-date')[:10]
        
        # Calculate balance
        context['balance'] = customer.get_balance()
        
        return context


class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'dairy_app/customer_form.html'
    success_url = reverse_lazy('customer_list')
    
    def form_valid(self, form):
        # Use the first admin user as default owner for all records
        first_user = User.objects.filter(is_superuser=True).first() or self.request.user
        form.instance.user = first_user
        messages.success(self.request, f"Customer '{form.instance.name}' created successfully!")
        return super().form_valid(form)


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'dairy_app/customer_form.html'
    
    def get_queryset(self):
        # Return all customers
        return Customer.objects.all()
    
    def get_success_url(self):
        return reverse_lazy('customer_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f"Customer '{form.instance.name}' updated successfully!")
        return super().form_valid(form)


class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    model = Customer
    template_name = 'dairy_app/customer_confirm_delete.html'
    success_url = reverse_lazy('customer_list')
    
    def get_queryset(self):
        # Return all customers
        return Customer.objects.all()
    
    def delete(self, request, *args, **kwargs):
        customer = self.get_object()
        messages.success(request, f"Customer '{customer.name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)


# Sale Views
class SaleListView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = 'dairy_app/sale_list.html'
    context_object_name = 'sales'
    paginate_by = 20
    
    def get_queryset(self):
        # Return all sales
        return Sale.objects.all().order_by('-date')


@login_required
def get_milk_types_for_customer(request):
    """AJAX view to get milk types for a customer"""
    customer_id = request.GET.get('customer_id')
    if customer_id:
        try:
            customer = Customer.objects.get(id=customer_id)
            milk_types = list(customer.milk_types.values('id', 'name'))
            
            # If the customer doesn't have any milk types assigned, return all available milk types
            if not milk_types:
                milk_types = list(MilkType.objects.all().values('id', 'name'))
                
            return JsonResponse({'milk_types': milk_types})
        except Customer.DoesNotExist:
            return JsonResponse({'error': 'Customer not found'}, status=404)
    return JsonResponse({'error': 'No customer ID provided'}, status=400)


@login_required
def get_all_milk_types(request):
    """AJAX view to get all milk types regardless of customer"""
    milk_types = list(MilkType.objects.all().values('id', 'name'))
    return JsonResponse({'milk_types': milk_types})

@login_required
def sale_create_view(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)
            # Use the first admin user as default owner for all records
            first_user = User.objects.filter(is_superuser=True).first() or request.user
            sale.user = first_user
            # If rate not provided, use the milk type's rate
            if not sale.rate:
                sale.rate = sale.milk_type.rate_per_liter
            sale.save()
            messages.success(request, "Sale recorded successfully!")
            return redirect('sale_list')
    else:
        # Check if customer parameter is passed in URL
        customer_id = request.GET.get('customer')
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
                form = SaleForm(initial={'customer': customer})
            except Customer.DoesNotExist:
                form = SaleForm()
        else:
            form = SaleForm()
    
    return render(request, 'dairy_app/sale_form.html', {'form': form})


@login_required
def batch_sale_input(request):
    """View for batch input of sales."""
    if request.method == 'POST':
        form = SaleInputForm(request.POST)
        if form.is_valid():
            customer = form.cleaned_data['customer']
            date = form.cleaned_data['date']
            sales_input = form.cleaned_data['sales_input']
            
            # Get all milk types
            all_milk_types = MilkType.objects.all()
            type_map = {}
            for milk_type in all_milk_types:
                first_letter = milk_type.name[0].upper()
                type_map[first_letter] = milk_type
                
            # Split input by '-'
            parts = sales_input.split('-')
            if len(parts) >= 3:
                quantities = parts[:-1]  # All but the last part are quantities
                type_codes = list(parts[-1].upper())  # Last part contains type codes
                
                if len(quantities) == len(type_codes):
                    # Create sales records
                    created_sales = 0
                    # Use the first admin user as default owner for all records
                    first_user = User.objects.filter(is_superuser=True).first() or request.user
                    
                    for i in range(len(quantities)):
                        try:
                            quantity = Decimal(quantities[i])
                            type_code = type_codes[i]
                            
                            if type_code in type_map:
                                milk_type = type_map[type_code]
                                # Create the sale record
                                Sale.objects.create(
                                    user=first_user,
                                    customer=customer,
                                    milk_type=milk_type,
                                    date=date,
                                    quantity=quantity,
                                    rate=milk_type.rate_per_liter
                                )
                                created_sales += 1
                            else:
                                messages.error(request, f"Milk type code '{type_code}' is not available.")
                        except (ValueError, IndexError):
                            messages.error(request, f"Invalid input format: {sales_input}")
                            return render(request, 'dairy_app/sale_batch_input.html', {'form': form})
                            
                    if created_sales > 0:
                        messages.success(request, f"{created_sales} sales recorded successfully!")
                        return redirect('sale_list')
                    else:
                        messages.error(request, "No valid sales were created. Please check the milk type codes.")
                else:
                    messages.error(request, "The number of quantities should match the number of milk type codes.")
            else:
                messages.error(request, "Invalid input format. Use format like '1-2-B'.")
    else:
        form = SaleInputForm()
        
    # Pass all milk types to the template
    milk_types = MilkType.objects.all()
    return render(request, 'dairy_app/sale_batch_input.html', {'form': form, 'milk_types': milk_types})


class SaleUpdateView(LoginRequiredMixin, UpdateView):
    model = Sale
    form_class = SaleForm
    template_name = 'dairy_app/sale_form.html'
    success_url = reverse_lazy('sale_list')
    
    def get_queryset(self):
        # Return all sales
        return Sale.objects.all()
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, "Sale updated successfully!")
        return super().form_valid(form)


class SaleDeleteView(LoginRequiredMixin, DeleteView):
    model = Sale
    template_name = 'dairy_app/sale_confirm_delete.html'
    success_url = reverse_lazy('sale_list')
    
    def get_queryset(self):
        # Return all sales
        return Sale.objects.all()
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Sale deleted successfully!")
        return super().delete(request, *args, **kwargs)


# Payment Views
class PaymentListView(LoginRequiredMixin, ListView):
    model = Payment
    template_name = 'dairy_app/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 20
    
    def get_queryset(self):
        # Return all payments
        return Payment.objects.all().order_by('-date')


@login_required
def payment_create_view(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            # Use the first admin user as default owner for all records
            first_user = User.objects.filter(is_superuser=True).first() or request.user
            payment.user = first_user
            payment.save()
            messages.success(request, "Payment recorded successfully!")
            return redirect('payment_list')
    else:
        # Check if customer parameter is passed in URL
        customer_id = request.GET.get('customer')
        if customer_id:
            try:
                customer = Customer.objects.get(id=customer_id)
                form = PaymentForm(initial={'customer': customer})
            except Customer.DoesNotExist:
                form = PaymentForm()
        else:
            form = PaymentForm()
    
    return render(request, 'dairy_app/payment_form.html', {'form': form})


class PaymentUpdateView(LoginRequiredMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'dairy_app/payment_form.html'
    success_url = reverse_lazy('payment_list')
    
    def get_queryset(self):
        # Return all payments
        return Payment.objects.all()
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, "Payment updated successfully!")
        return super().form_valid(form)


class PaymentDeleteView(LoginRequiredMixin, DeleteView):
    model = Payment
    template_name = 'dairy_app/payment_confirm_delete.html'
    success_url = reverse_lazy('payment_list')
    
    def get_queryset(self):
        # Return all payments
        return Payment.objects.all()
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Payment deleted successfully!")
        return super().delete(request, *args, **kwargs)


# Report Views
@login_required
def daily_report_view(request):
    """View for displaying daily sales summary"""
    today = timezone.now().date()
    
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
        else:
            start_date = today - timedelta(days=30)
            end_date = today
    else:
        form = DateRangeForm(initial={'start_date': today - timedelta(days=30), 'end_date': today})
        start_date = today - timedelta(days=30)
        end_date = today
    
    # Get daily sales data - removed user filter
    daily_sales = Sale.objects.filter(
        date__gte=start_date, 
        date__lte=end_date
    ).values('date', 'milk_type__name').annotate(
        total_quantity=Sum('quantity'),
        total_amount=Sum(F('quantity') * F('rate'), output_field=DecimalField())
    ).order_by('date')
    
    # Organize the data by date
    report_data = {}
    for sale in daily_sales:
        date_str = sale['date'].strftime('%Y-%m-%d')
        if date_str not in report_data:
            report_data[date_str] = {
                'date': sale['date'],
                'milk_types': {},
                'total_quantity': 0,
                'total_amount': 0,
            }
        
        report_data[date_str]['milk_types'][sale['milk_type__name']] = {
            'quantity': sale['total_quantity'],
            'amount': sale['total_amount']
        }
        
        report_data[date_str]['total_quantity'] += sale['total_quantity']
        report_data[date_str]['total_amount'] += sale['total_amount']
    
    # Convert to a list sorted by date
    report_list = [report_data[date_str] for date_str in sorted(report_data.keys(), reverse=True)]
    
    # Calculate total quantities and amounts for the entire period
    total_quantity = sum(day_data['total_quantity'] for day_data in report_list)
    total_amount = sum(day_data['total_amount'] for day_data in report_list)
    
    context = {
        'form': form,
        'report_data': report_list,
        'start_date': start_date,
        'end_date': end_date,
        'total_quantity': total_quantity,
        'total_amount': total_amount,
    }
    
    return render(request, 'dairy_app/daily_report.html', context)


@login_required
def monthly_report_view(request):
    """View for displaying monthly sales summary"""
    today = timezone.now().date()
    
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
        else:
            # Default to current year
            start_date = today.replace(month=1, day=1)
            end_date = today
    else:
        # Default to current year
        form = DateRangeForm(initial={
            'start_date': today.replace(month=1, day=1),
            'end_date': today
        })
        start_date = today.replace(month=1, day=1)
        end_date = today
    
    # Get monthly sales data - removed user filter
    monthly_sales = Sale.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total_quantity=Sum('quantity'),
        total_amount=Sum(F('quantity') * F('rate'), output_field=DecimalField())
    ).order_by('month')
    
    # Get monthly payment data - removed user filter
    monthly_payments = Payment.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total_amount=Sum('amount')
    ).order_by('month')
    
    # Organize the data by month
    report_data = {}
    for sale in monthly_sales:
        month_str = sale['month'].strftime('%Y-%m')
        if month_str not in report_data:
            report_data[month_str] = {
                'month': sale['month'],
                'total_quantity': sale['total_quantity'],
                'total_amount': sale['total_amount'],
                'total_payment': 0,
                'balance': 0,
            }
        else:
            report_data[month_str]['total_quantity'] += sale['total_quantity']
            report_data[month_str]['total_amount'] += sale['total_amount']
    
    for payment in monthly_payments:
        month_str = payment['month'].strftime('%Y-%m')
        if month_str in report_data:
            report_data[month_str]['total_payment'] += payment['total_amount']
        else:
            report_data[month_str] = {
                'month': payment['month'],
                'total_quantity': 0,
                'total_amount': 0,
                'total_payment': payment['total_amount'],
                'balance': 0,
            }
    
    # Calculate balance for each month
    for month_str, data in report_data.items():
        data['balance'] = data['total_amount'] - data['total_payment']
    
    # Convert to a list sorted by month
    report_list = [report_data[month_str] for month_str in sorted(report_data.keys(), reverse=True)]
    
    # Calculate totals for the entire period
    total_quantity = sum(month_data['total_quantity'] for month_data in report_list)
    total_sales = sum(month_data['total_amount'] for month_data in report_list)
    total_payments = sum(month_data['total_payment'] for month_data in report_list)
    total_balance = total_sales - total_payments
    
    context = {
        'form': form,
        'report_data': report_list,
        'start_date': start_date,
        'end_date': end_date,
        'total_quantity': total_quantity,
        'total_sales': total_sales,
        'total_payments': total_payments,
        'total_balance': total_balance,
    }
    
    return render(request, 'dairy_app/monthly_report.html', context)


@login_required
def customer_balance_report_view(request):
    """View for displaying customer balance report"""
    # Get all customers instead of filtering by user
    customers = Customer.objects.all()
    customer_data = []
    
    for customer in customers:
        total_sales = Sale.objects.filter(customer=customer).aggregate(
            total=Sum(F('quantity') * F('rate'), output_field=DecimalField())
        )['total'] or 0
        
        total_payments = Payment.objects.filter(customer=customer).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        balance = total_sales - total_payments
        
        customer_data.append({
            'customer': customer,
            'total_sales': total_sales,
            'total_payments': total_payments,
            'balance': balance
        })
    
    # Sort by balance (highest first)
    customer_data.sort(key=lambda x: x['balance'], reverse=True)
    
    context = {
        'customer_data': customer_data
    }
    
    return render(request, 'dairy_app/customer_balance_report.html', context)


@login_required
def get_milk_types_for_customer(request):
    """AJAX view to get milk types for a specific customer"""
    customer_id = request.GET.get('customer_id')
    
    if not customer_id:
        return JsonResponse({'error': 'No customer ID provided'}, status=400)
    
    try:
        customer = Customer.objects.get(id=customer_id)
        milk_types = customer.milk_types.all()
        
        milk_types_data = [
            {
                'id': milk_type.id, 
                'name': milk_type.name,
                'rate_per_liter': float(milk_type.rate_per_liter)
            } 
            for milk_type in milk_types
        ]
        
        return JsonResponse({'milk_types': milk_types_data})
    
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)

def get_all_milk_types(request):
    """Return all available milk types."""
    milk_types = list(MilkType.objects.all().values('id', 'name'))
    return JsonResponse({'milk_types': milk_types})

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
import datetime
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
    paginate_by = 25  # Show 25 customers per page
    
    def highlight_text(self, text, search_term):
        """Helper method to highlight search term in text"""
        if not search_term:
            return text
        
        # Use case-insensitive replacement
        search_term_lower = search_term.lower()
        text_lower = text.lower()
        
        result = ""
        last_end = 0
        
        # Find all occurrences of the search term and wrap them with highlight spans
        start = text_lower.find(search_term_lower)
        while start != -1:
            # Add the text before the match
            result += text[last_end:start]
            
            # Add the highlighted match
            match_end = start + len(search_term)
            result += f'<span class="search-highlight">{text[start:match_end]}</span>'
            
            # Move past this match
            last_end = match_end
            start = text_lower.find(search_term_lower, last_end)
        
        # Add any remaining text
        if last_end < len(text):
            result += text[last_end:]
            
        return result
    
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
        
        # Get all customer IDs from the current page
        customer_ids = [customer.id for customer in context['customers']]
        
        # Get the monthly milk delivery data for just the customers on this page
        monthly_sales = Sale.objects.filter(
            customer_id__in=customer_ids,
            date__gte=start_of_month,
            date__lte=today
        ).values('customer_id', 'milk_type__name').annotate(
            total_quantity=Sum('quantity')
        )
        
        # Organize sales by customer
        milk_delivery_by_customer = {}
        for sale in monthly_sales:
            customer_id = sale['customer_id']
            milk_type_name = sale['milk_type__name']
            quantity = sale['total_quantity']
            
            if customer_id not in milk_delivery_by_customer:
                milk_delivery_by_customer[customer_id] = {}
            
            milk_delivery_by_customer[customer_id][milk_type_name] = quantity
        
        # Get balance data for customers on current page
        for customer in context['customers']:
            # Get milk delivery data (already calculated)
            milk_delivery = milk_delivery_by_customer.get(customer.id, {})
            
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
        
        # Get search query for highlighting
        search_query = self.request.GET.get('search', '').strip()
        
        # Highlight customer names if there's a search query
        if search_query:
            for customer in context['customers']:
                customer.highlighted_name = self.highlight_text(customer.name, search_query)
        
        # Add custom pagination information
        page_obj = context['page_obj']
        paginator = context['paginator']
        
        # Create a list of page numbers to display
        page_range = list(paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1))
        
        context['customer_data'] = customer_data
        context['milk_types'] = all_milk_types
        context['search_query'] = search_query
        context['current_month'] = today.strftime('%B %Y')
        context['page_range'] = page_range
        context['total_customers'] = paginator.count
        
        return context
        
    def get(self, request, *args, **kwargs):
        # Check if request is AJAX, but only consider it AJAX if the special custom parameter is set
        is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 
                  request.GET.get('ajax_search') == 'true')
        
        if is_ajax:
            # For AJAX requests, we need all matching customers, not just the current page
            # This is to preserve the search functionality that works across all customers
            queryset = self.get_queryset()
            search_query = request.GET.get('search', '').strip()
            
            # Calculate the data we need for display
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            customer_data = {}
            
            # Get all matching customer IDs
            customer_ids = list(queryset.values_list('id', flat=True))
            
            # Get the monthly milk delivery data in bulk
            monthly_sales = Sale.objects.filter(
                customer_id__in=customer_ids,
                date__gte=start_of_month,
                date__lte=today
            ).values('customer_id', 'milk_type__name').annotate(
                total_quantity=Sum('quantity')
            )
            
            # Organize sales by customer
            milk_delivery_by_customer = {}
            for sale in monthly_sales:
                customer_id = sale['customer_id']
                milk_type_name = sale['milk_type__name']
                quantity = sale['total_quantity']
                
                if customer_id not in milk_delivery_by_customer:
                    milk_delivery_by_customer[customer_id] = {}
                
                milk_delivery_by_customer[customer_id][milk_type_name] = quantity
            
            # Get balance data for all matching customers in bulk
            sales_by_customer = Sale.objects.filter(
                customer_id__in=customer_ids
            ).values('customer_id').annotate(
                total=Sum(F('quantity') * F('rate'), output_field=DecimalField())
            )
            
            payments_by_customer = Payment.objects.filter(
                customer_id__in=customer_ids
            ).values('customer_id').annotate(
                total=Sum('amount')
            )
            
            # Convert to dictionaries for faster lookup
            sales_dict = {item['customer_id']: item['total'] for item in sales_by_customer}
            payments_dict = {item['customer_id']: item['total'] for item in payments_by_customer}
            
            # Calculate balance for each customer
            for customer_id in customer_ids:
                total_sales = sales_dict.get(customer_id, 0) or 0
                total_payments = payments_dict.get(customer_id, 0) or 0
                balance = total_sales - total_payments
                
                customer_data[customer_id] = {
                    'milk_delivery': milk_delivery_by_customer.get(customer_id, {}),
                    'balance': balance
                }
            
            # Format the response
            html_content = []
            
            for idx, customer in enumerate(queryset):
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
                
                # Highlight the customer name if there's a search query
                customer_name = customer.name
                highlighted_name = self.highlight_text(customer_name, search_query) if search_query else customer_name
                
                # Create row
                row = {
                    'counter': idx + 1,
                    'id': customer.id,
                    'name': customer_name,
                    'highlighted_name': highlighted_name,
                    'milk_types_html': milk_types_html,
                    'delivery_html': delivery_html,
                    'balance_html': balance_html
                }
                
                html_content.append(row)
            
            # Return JSON response with all matching customers
            return JsonResponse({
                'customers': html_content,
                'total_count': len(html_content)
            })
            
        # Regular request - proceed as normal with pagination
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
        
        # Get selected month and year for monthly consumption
        today = timezone.now().date()
        selected_month = self.request.GET.get('month', today.month)
        selected_year = self.request.GET.get('year', today.year)
        
        try:
            selected_month = int(selected_month)
            selected_year = int(selected_year)
            # Validate month and year
            if not 1 <= selected_month <= 12:
                selected_month = today.month
            if not 2000 <= selected_year <= 2100:
                selected_year = today.year
        except (ValueError, TypeError):
            selected_month = today.month
            selected_year = today.year
            
        # Generate start and end dates for the selected month
        start_date = datetime.date(selected_year, selected_month, 1)
        if selected_month == 12:
            end_date = datetime.date(selected_year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            end_date = datetime.date(selected_year, selected_month + 1, 1) - datetime.timedelta(days=1)
            
        # Get milk types this customer uses
        milk_types = customer.milk_types.all()
        
        # Get daily sales data for the selected month
        sales_data = Sale.objects.filter(
            customer=customer,
            date__gte=start_date,
            date__lte=end_date
        ).values('date', 'milk_type__name', 'quantity')
        
        # Organize sales by date
        monthly_consumption = {}
        for day in range(1, end_date.day + 1):
            # Initialize each day with zeros for each milk type
            current_date = datetime.date(selected_year, selected_month, day)
            monthly_consumption[day] = {
                'date': current_date,
                'milk_data': {milk_type.name: Decimal('0.0') for milk_type in milk_types},
                'total': Decimal('0.0')
            }
        
        # Fill in actual sales data
        for sale in sales_data:
            day = sale['date'].day
            milk_type = sale['milk_type__name']
            quantity = sale['quantity']
            
            # Add the quantity to the appropriate day and milk type
            if milk_type in monthly_consumption[day]['milk_data']:
                monthly_consumption[day]['milk_data'][milk_type] += quantity
            else:
                monthly_consumption[day]['milk_data'][milk_type] = quantity
                
            # Update day's total
            monthly_consumption[day]['total'] += quantity
        
        # Calculate monthly totals by milk type
        milk_type_totals = {milk_type.name: Decimal('0.0') for milk_type in milk_types}
        month_total = Decimal('0.0')
        
        for day_data in monthly_consumption.values():
            for milk_type, quantity in day_data['milk_data'].items():
                milk_type_totals[milk_type] += quantity
                month_total += quantity
        
        # Add context variables
        context['monthly_consumption'] = monthly_consumption
        context['milk_type_totals'] = milk_type_totals
        context['month_total'] = month_total
        context['selected_month'] = selected_month
        context['selected_year'] = selected_year
        context['milk_types'] = milk_types
        context['month_name'] = start_date.strftime('%B')
        
        # Generate month/year options for dropdown
        context['month_options'] = [
            {'number': m, 'name': datetime.date(2000, m, 1).strftime('%B')}
            for m in range(1, 13)
        ]
        
        current_year = today.year
        context['year_options'] = range(current_year - 2, current_year + 1)
        
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

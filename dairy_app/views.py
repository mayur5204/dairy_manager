from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _

# Import ReportLab for PDF generation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import cm, inch, mm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import os
import tempfile
from PyPDF2 import PdfReader, PdfWriter
from django.conf import settings

from .models import MilkType, Customer, Sale, Payment, Area, MonthlyBalance
from .forms import (
    MilkTypeForm, CustomerForm, SaleForm, 
    SaleInputForm, PaymentForm, DateRangeForm, MonthSelectionForm,
    AreaForm
)

import re
import datetime
from datetime import timedelta
from decimal import Decimal

# Dashboard View
@login_required
def dashboard_view(request):
    """Main dashboard view showing summary data"""
    today = timezone.now().date()
    
    # Get customers count
    customers_count = Customer.objects.all().count()
    
    # Get areas count
    areas_count = Area.objects.filter(user=request.user).count()
    
    # Get recent activities
    recent_sales = Sale.objects.order_by('-created_at')[:5]  # Order by creation time
    recent_payments = Payment.objects.order_by('-created_at')[:5] # Order by creation time
    
    context = {
        'customers_count': customers_count,
        'areas_count': areas_count,
        'recent_sales': recent_sales,
        'recent_payments': recent_payments,
        'today': today,
    }
    
    return render(request, 'dairy_app/dashboard.html', context)


# Search API for Customers
@login_required
def search_customers(request):
    """AJAX view to search customers by name"""
    search_query = request.GET.get('search', '').strip()
    results = []
    
    if search_query:
        # Search for customers by name
        customers = Customer.objects.filter(name__icontains=search_query)[:10]  # Limit to 10 results
        
        # Format results with highlighting
        for idx, customer in enumerate(customers):
            # Highlight the matching part of the name
            name = customer.name
            query_lower = search_query.lower()
            name_lower = name.lower()
            
            highlighted_name = ""
            last_end = 0
            
            # Find all occurrences of the search term and wrap them with highlight spans
            start = name_lower.find(query_lower)
            while start != -1:
                # Add the text before the match
                highlighted_name += name[last_end:start]
                
                # Add the highlighted match
                match_end = start + len(search_query)
                highlighted_name += f'<span class="search-highlight">{name[start:match_end]}</span>'
                
                # Move past this match
                last_end = match_end
                start = name_lower.find(query_lower, last_end)
            
            # Add any remaining text
            if last_end < len(name):
                highlighted_name += name[last_end:]
            
            results.append({
                'id': customer.id,
                'name': customer.name,
                'highlighted_name': highlighted_name,
                'counter': idx + 1
            })
    
    return JsonResponse({'customers': results})

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


# Area Views
class AreaListView(LoginRequiredMixin, ListView):
    model = Area
    template_name = 'dairy_app/area_list.html'
    context_object_name = 'areas'
    
    def get_queryset(self):
        # Show areas for current user
        return Area.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add customer counts for each area
        for area in context['areas']:
            area.customer_count = area.get_customer_count()
        return context


class AreaCreateView(LoginRequiredMixin, CreateView):
    model = Area
    form_class = AreaForm
    template_name = 'dairy_app/area_form.html'
    success_url = reverse_lazy('area_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Set the current user as the owner
        form.instance.user = self.request.user
        messages.success(self.request, f"Area '{form.instance.name}' created successfully!")
        return super().form_valid(form)


class AreaUpdateView(LoginRequiredMixin, UpdateView):
    model = Area
    form_class = AreaForm
    template_name = 'dairy_app/area_form.html'
    success_url = reverse_lazy('area_list')
    
    def get_queryset(self):
        # Only allow users to edit their own areas
        return Area.objects.filter(user=self.request.user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, f"Area '{form.instance.name}' updated successfully!")
        return super().form_valid(form)


class AreaDeleteView(LoginRequiredMixin, DeleteView):
    model = Area
    template_name = 'dairy_app/area_confirm_delete.html'
    success_url = reverse_lazy('area_list')
    
    def get_queryset(self):
        # Only allow users to delete their own areas
        return Area.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        area = self.get_object()
        messages.success(request, f"Area '{area.name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)


@login_required
def area_customers_view(request, pk):
    """View customers for a specific area"""
    area = get_object_or_404(Area, pk=pk, user=request.user)
    customers = Customer.objects.filter(area=area)
    
    context = {
        'area': area,
        'customers': customers
    }
    
    return render(request, 'dairy_app/area_customers.html', context)


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
        
        # Filter by area if specified
        area_id = self.request.GET.get('area')
        if area_id:
            try:
                queryset = queryset.filter(area_id=area_id)
            except ValueError:
                pass
                
        # Filter by search term
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
        
        # Add areas for filtering
        areas = Area.objects.filter(user=self.request.user)
        context['areas'] = areas
        
        # Check if an area filter is active
        area_id = self.request.GET.get('area')
        if area_id:
            try:
                context['selected_area'] = int(area_id)
            except ValueError:
                pass
        
        # Add custom pagination information
        page_obj = context['page_obj']
        paginator = context['paginator']
        
        # Create a list of page numbers to display
        page_range = list(paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1))
        
        context.update({
            'customer_data': customer_data,
            'milk_types': all_milk_types,
            'search_query': search_query,
            'current_month': today.strftime('%B %Y'),
            'page_range': page_range,
            'total_customers': paginator.count
        })
        
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
        context['recent_sales'] = Sale.objects.filter(customer=customer).order_by('-created_at')[:10] # Order by creation time
        
        # Get recent payments
        context['recent_payments'] = Payment.objects.filter(customer=customer).order_by('-created_at')[:10] # Order by creation time
        
        # Calculate balance
        context['balance'] = customer.get_balance()
        
        # Add current month and year for bill generation
        today = timezone.now().date()
        context['current_month'] = today.month
        context['current_month_name'] = today.strftime('%B')
        context['current_year'] = today.year
        
        # Import translation functions for month names
        from django.utils.translation import gettext_lazy as _
        from django.utils.dates import MONTHS
        
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
                if milk_type not in milk_type_totals:
                    milk_type_totals[milk_type] = Decimal('0.0')
                milk_type_totals[milk_type] += quantity
                month_total += quantity
        
        # Ensure all milk types are initialized in milk_type_totals
        for milk_type in milk_types:
            if milk_type.name not in milk_type_totals:
                milk_type_totals[milk_type.name] = Decimal('0.0')
        
        # Ensure all milk types are initialized in milk_type_totals
        all_milk_types = MilkType.objects.all()
        for milk_type in all_milk_types:
            if milk_type.name not in milk_type_totals:
                milk_type_totals[milk_type.name] = Decimal('0.0')
        
        # Add context variables
        context['monthly_consumption'] = monthly_consumption
        context['milk_type_totals'] = milk_type_totals
        context['month_total'] = month_total
        context['selected_month'] = selected_month
        context['selected_year'] = selected_year
        context['milk_types'] = milk_types
        
        # Get monthly balance information
        # First, update the monthly balances for this customer to ensure they're current
        customer.get_monthly_balances(update=True)
        
        # Get monthly balance for the selected month
        month_balance_info = customer.get_month_balance(selected_year, selected_month)
        context['month_balance_info'] = month_balance_info
        
        # Get pending months (months with unpaid balances)
        context['pending_months'] = customer.get_pending_months()
        
        # Get all monthly balances
        context['monthly_balances'] = MonthlyBalance.objects.filter(
            customer=customer
        ).order_by('-year', '-month')[:12]  # Show last 12 months
        
        # Get payment allocations for each month
        from django.db.models import Prefetch
        try:
            from .models import PaymentAllocation
            context['has_allocations'] = True
            
            # Get all payment allocations for this customer
            allocations = PaymentAllocation.objects.filter(
                payment__customer=customer
            ).select_related('payment').order_by('-payment__date')[:20]
            
            context['payment_allocations'] = allocations
        except ImportError:
            # PaymentAllocation model may not be available yet (during migrations)
            context['has_allocations'] = False
        
        # Use translated month name instead of strftime
        context['month_name'] = _(MONTHS[selected_month])
        
        # Generate month options with translated names
        context['month_options'] = [
            {'number': m, 'name': _(MONTHS[m])}
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
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
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
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
        
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
    
    def get_context_data(self, **kwargs):
        # Add additional context with translations
        context = super().get_context_data(**kwargs)
        from django.utils.translation import gettext as _
        
        # Add explicitly translated common texts
        context.update({
            'page_title': _('Delete Customer'),
            'confirm_delete_title': _('Confirm Delete'),
            'confirm_prompt': _('Are you sure you want to delete this customer?'),
            'warning_text': _('Warning!'),
            'customer_has': _('This customer has:'),
            'sales_record': _('sales record'),
            'payment_record': _('payment record'),
            'delete_warning': _('Deleting this customer will make those records reference a deleted customer.'),
            'cancel_button': _('Cancel'),
            'delete_button': _('Delete Permanently'),
            'back_to_details': _('Back to Details'),
        })
        
        return context
    
    def delete(self, request, *args, **kwargs):
        customer = self.get_object()
        messages.success(request, _("Customer '%(name)s' deleted successfully!") % {'name': customer.name})
        return super().delete(request, *args, **kwargs)


# Sale Views
class SaleListView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = 'dairy_app/sale_list.html'
    context_object_name = 'sales'
    paginate_by = 20
    
    def get_queryset(self):
        # Return all sales ordered by creation time (newest first)
        return Sale.objects.all().order_by('-created_at')


@login_required
def get_milk_types_for_customer(request):
    """AJAX view to get milk types for a customer"""
    customer_id = request.GET.get('customer_id')
    if customer_id:
        try:
            customer = Customer.objects.get(id=customer_id)
            milk_types = list(customer.milk_types.all())
            
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
    return JsonResponse({'error': 'No customer ID provided'}, status=400)


@login_required
def get_all_milk_types(request):
    """AJAX view to get all milk types regardless of customer"""
    milk_types = list(MilkType.objects.all().values('id', 'name'))
    return JsonResponse({'milk_types': milk_types})

@login_required
def sale_create_view(request):
    customer = None
    customer_milk_types = []
    search_results = None
    from_customer_page = False
    
    # Check if user is coming from customer detail page
    referer = request.META.get('HTTP_REFERER', '')
    from_customer_page = '/customers/' in referer
    
    # If no customer selected and not from customer page, redirect to customer list with search
    if not request.GET.get('customer') and not from_customer_page:
        return redirect('customer_list')
    
    # Handle search query
    search_query = request.GET.get('search', '').strip()
    if search_query:
        search_results = Customer.objects.filter(name__icontains=search_query)
    
    # Handle customer selection
    customer_id = request.GET.get('customer')
    last_sale_quantities = {}
    
    if customer_id:
        try:
            customer = Customer.objects.get(id=customer_id)
            customer_milk_types = customer.milk_types.all()
            
            # Get the last sale quantity for each milk type for this customer
            for milk_type in customer_milk_types:
                last_sale = Sale.objects.filter(
                    customer=customer, 
                    milk_type=milk_type
                ).order_by('-created_at').first()
                
                if last_sale:
                    last_sale_quantities[milk_type.id] = last_sale.quantity
            
            form = SaleForm(initial={'customer': customer})
        except Customer.DoesNotExist:
            form = SaleForm()
    else:
        form = SaleForm()

    if request.method == 'POST':
        # Check if we're handling batch input
        if 'milk_types[]' in request.POST:
            milk_type_ids = request.POST.getlist('milk_types[]')
            quantities = request.POST.getlist('quantities[]')
            customer_id = request.POST.get('customer')
            date = request.POST.get('date')
            
            # Use the first admin user as default owner for all records
            first_user = User.objects.filter(is_superuser=True).first() or request.user
            
            # Validate and create sales for each selected milk type
            sales_created = 0
            try:
                customer = Customer.objects.get(id=customer_id)
                
                # Create a sale for each selected milk type with a quantity
                for i, milk_type_id in enumerate(milk_type_ids):
                    # Skip if no quantity or invalid quantity
                    if i >= len(quantities) or not quantities[i]:
                        continue
                    
                    try:
                        quantity = Decimal(quantities[i])
                        if quantity <= 0:
                            continue
                            
                        try:
                            milk_type = MilkType.objects.get(id=milk_type_id)
                            
                            # Create the sale
                            Sale.objects.create(
                                user=first_user,
                                customer=customer,
                                milk_type=milk_type,
                                date=date,
                                quantity=quantity,
                                rate=milk_type.rate_per_liter,
                                notes=''  # Empty string instead of retrieving from POST
                            )
                            sales_created += 1
                        except MilkType.DoesNotExist:
                            messages.error(request, f"Invalid milk type selected")
                    except (ValueError, TypeError):
                        messages.error(request, f"Invalid quantity provided")
                
                if sales_created > 0:
                    messages.success(request, f"{sales_created} sales recorded successfully!")
                    return redirect('sale_list')
                else:
                    messages.error(request, "No valid sales were created. Please check your input.")
            except Customer.DoesNotExist:
                messages.error(request, "Invalid customer selected")
        else:
            # Handle regular single sale form
            form = SaleForm(request.POST)
            if form.is_valid():
                sale = form.save(commit=False)
                # Use the first admin user as default owner for all records
                first_user = User.objects.filter(is_superuser=True).first() or request.user
                sale.user = first_user
                # If rate not provided, use the milk type's rate
                if not sale.rate:
                    sale.rate = sale.milk_type.rate_per_liter
                # Set notes to empty string
                sale.notes = ''
                sale.save()
                messages.success(request, "Sale recorded successfully!")
                return redirect('sale_list')
    
    context = {
        'form': form,
        'customer': customer,
        'from_customer_page': from_customer_page,
        'customer_milk_types': customer_milk_types,
        'search_results': search_results,
        'last_sale_quantities': last_sale_quantities,
    }
    
    return render(request, 'dairy_app/sale_form.html', context)


class SaleUpdateView(LoginRequiredMixin, UpdateView):
    model = Sale
    form_class = SaleForm
    template_name = 'dairy_app/sale_form.html'
    success_url = reverse_lazy('sale_list')
    
    def get_queryset(self):
        # Return all sales
        return Sale.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add customer to context so the template doesn't redirect to search
        context['customer'] = self.object.customer
        # Add customer milk types to context
        context['customer_milk_types'] = self.object.customer.milk_types.all()
        
        # Add the current milk type and quantity for pre-selection in form
        context['current_milk_type_id'] = self.object.milk_type.id
        context['current_quantity'] = self.object.quantity
        context['current_rate'] = self.object.rate
        return context
    
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
        # Return all payments ordered by creation time (newest first)
        return Payment.objects.all().order_by('-created_at')


@login_required
def payment_create_view(request):
    customer = None
    search_results = None
    from_customer_page = False
    
    # Check if user is coming from customer detail page
    referer = request.META.get('HTTP_REFERER', '')
    from_customer_page = '/customers/' in referer
    
    # If no customer selected and not from customer page, redirect to customer list with search
    if not request.GET.get('customer') and not from_customer_page:
        return redirect('customer_list')
    
    # Handle search query
    search_query = request.GET.get('search', '').strip()
    if search_query:
        search_results = Customer.objects.filter(name__icontains=search_query)
    
    # Handle customer selection
    customer_id = request.GET.get('customer')
    fetch_unpaid = request.GET.get('fetch_unpaid') == 'true'
    
    if customer_id:
        try:
            customer = Customer.objects.get(id=customer_id)
            form = PaymentForm(initial={'customer': customer})
            
            # Always fetch unpaid months for the selected customer to ensure they're available
            # Force recalculation first for accurate data
            MonthlyBalance.update_monthly_balances(customer)
            form.unpaid_months = form.get_unpaid_months(customer)
            
            # For AJAX requests, we can return just the unpaid months section
            if fetch_unpaid and 'HTTP_X_REQUESTED_WITH' in request.META:
                # Render the partial template with just the unpaid months
                return render(request, 'dairy_app/payment_form_partial.html', {
                    'form': form,
                    'customer': customer
                })
                
        except Customer.DoesNotExist:
            form = PaymentForm()
        except Exception as e:
            form = PaymentForm()
    else:
        form = PaymentForm()

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            # Use the first admin user as default owner for all records
            first_user = User.objects.filter(is_superuser=True).first() or request.user
            payment.user = first_user
            
            # Check if this is a multi-month payment
            is_multi_month = form.cleaned_data.get('is_multi_month')
            
            # If using multi-month distribution, make sure payment_for_month/year are None
            if is_multi_month:
                payment.payment_for_month = None
                payment.payment_for_year = None
                
            payment.save()
            
            if is_multi_month and 'selected_months' in request.POST:
                # Process multiple month allocation
                selected_month_strings = request.POST.getlist('selected_months')
                
                # Parse the selected months from format "month_year"
                selected_months = []
                for month_str in selected_month_strings:
                    try:
                        month, year = month_str.split('_')
                        selected_months.append((int(month), int(year)))
                    except (ValueError, IndexError):
                        # Skip invalid formats
                        continue
                
                # Get all selected unpaid months
                unpaid_months = []
                amount_remaining = payment.amount
                
                # Get the customer's unpaid months
                unpaid_balances = MonthlyBalance.objects.filter(
                    customer=payment.customer,
                    is_paid=False,
                    sales_amount__gt=0
                ).order_by('year', 'month')  # Process oldest months first
                
                # Create allocations
                allocations = []
                for balance in unpaid_balances:
                    if (balance.month, balance.year) not in selected_months:
                        continue
                    
                    # Calculate how much to allocate to this month
                    owed_amount = balance.sales_amount - balance.payment_amount
                    allocation_amount = min(owed_amount, amount_remaining)
                    
                    if allocation_amount <= 0:
                        continue
                    
                    # Create allocation for this month
                    allocations.append({
                        'month': balance.month,
                        'year': balance.year,
                        'amount': allocation_amount
                    })
                    
                    amount_remaining -= allocation_amount
                    
                    # Stop if we've allocated all the payment
                    if amount_remaining <= 0:
                        break
                
                # Distribute payment across selected months
                if allocations:
                    payment.distribute_to_months(allocations)
                    
                    # Force recalculation of all monthly balances for this customer
                    # This ensures all allocations are properly accounted for
                    MonthlyBalance.update_monthly_balances(payment.customer)
            
            messages.success(request, "Payment recorded successfully!")
            
            # If coming from customer detail page, redirect back there
            if from_customer_page and customer:
                return redirect('customer_detail', pk=customer.id)
            return redirect('payment_list')
    
    context = {
        'form': form,
        'customer': customer,
        'from_customer_page': from_customer_page,
        'search_results': search_results,
    }
    
    return render(request, 'dairy_app/payment_form.html', context)


class PaymentUpdateView(LoginRequiredMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'dairy_app/payment_form.html'
    success_url = reverse_lazy('payment_list')
    
    def get_queryset(self):
        # Return all payments
        return Payment.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add customer to context so the template doesn't redirect to search
        context['customer'] = self.object.customer
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Force recalculation of all monthly balances for this customer 
        # after saving the payment to ensure accurate balances
        customer = self.object.customer
        MonthlyBalance.update_monthly_balances(customer)
        
        messages.success(self.request, "Payment updated successfully!")
        return response


class PaymentDeleteView(LoginRequiredMixin, DeleteView):
    model = Payment
    template_name = 'dairy_app/payment_confirm_delete.html'
    success_url = reverse_lazy('payment_list')
    
    def get_queryset(self):
        # Return all payments
        return Payment.objects.all()
    
    def delete(self, request, *args, **kwargs):
        # Get the customer before deleting the payment
        payment = self.get_object()
        customer = payment.customer
        
        # Delete the payment
        response = super().delete(request, *args, **kwargs)
        
        # Update the monthly balances for this customer
        MonthlyBalance.update_monthly_balances(customer)
        
        messages.success(request, "Payment deleted successfully!")
        return response


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
        form = MonthSelectionForm(request.POST)
        if form.is_valid():
            selected_month = int(form.cleaned_data['month'])
            selected_year = int(form.cleaned_data['year'])
        else:
            # Default to current month and year
            selected_month = today.month
            selected_year = today.year
    else:
        # Default to current month and year
        form = MonthSelectionForm(initial={
            'month': today.month,
            'year': today.year
        })
        selected_month = today.month
        selected_year = today.year
    
    # Generate start and end dates for the selected month
    start_date = datetime.date(selected_year, selected_month, 1)
    if selected_month == 12:
        end_date = datetime.date(selected_year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(selected_year, selected_month + 1, 1) - datetime.timedelta(days=1)
    
    # Get monthly sales data
    monthly_sales = Sale.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total_quantity=Sum('quantity'),
        total_amount=Sum(F('quantity') * F('rate'), output_field=DecimalField())
    ).order_by('month')
    
    # Get monthly payment data
    monthly_payments = Payment.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total_amount=Sum('amount')
    ).order_by('month')
    
    # Organize the data
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
    
    # Convert to a list
    report_list = [report_data[month_str] for month_str in sorted(report_data.keys())]
    
    # Calculate totals for the entire period
    total_quantity = sum(month_data['total_quantity'] for month_data in report_list)
    total_sales = sum(month_data['total_amount'] for month_data in report_list)
    total_payments = sum(month_data['total_payment'] for month_data in report_list)
    total_balance = total_sales - total_payments
    
    context = {
        'form': form,
        'report_data': report_list,
        'month_name': start_date.strftime('%B'),
        'year': selected_year,
        'total_quantity': total_quantity,
        'total_sales': total_sales,
        'total_payments': total_payments,
        'total_balance': total_balance,
    }
    
    return render(request, 'dairy_app/monthly_report.html', context)


@login_required
def customer_export_view(request):
    """View for displaying customer data export page with month/year selection"""
    # Get current date
    today = timezone.now().date()
    
    # Handle month/year selection
    if request.method == 'POST':
        selected_month = int(request.POST.get('month', today.month))
        selected_year = int(request.POST.get('year', today.year))
    else:
        selected_month = int(request.GET.get('month', today.month))
        selected_year = int(request.GET.get('year', today.year))
    
    # Validate month and year
    if not 1 <= selected_month <= 12:
        selected_month = today.month
    if not 2000 <= selected_year <= 2100:
        selected_year = today.year
    
    # Generate start and end dates for the selected month
    start_date = datetime.date(selected_year, selected_month, 1)
    if selected_month == 12:
        end_date = datetime.date(selected_year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(selected_year, selected_month + 1, 1) - datetime.timedelta(days=1)
    
    days_in_month = end_date.day
    day_range = range(1, days_in_month + 1)
    preview_days = min(7, days_in_month)  # Show only 7 days in preview
    
    # For better performance, limit to top 25 customers for web view
    customers = Customer.objects.all().order_by('name')[:25]
    
    # Pre-fetch all sales data for these customers in one query
    customer_ids = [customer.id for customer in customers]
    all_sales = Sale.objects.filter(
        customer_id__in=customer_ids,
        date__gte=start_date,
        date__lte=end_date
    ).select_related('milk_type').order_by('customer_id', 'milk_type_id', 'date')
    
    # Pre-fetch balance data for all customers at once
    all_customer_totals = {}
    
    # Get total sales for all customers in one query
    all_sales_totals = Sale.objects.filter(
        customer_id__in=customer_ids
    ).values('customer_id').annotate(
        total=Sum(F('quantity') * F('rate'), output_field=DecimalField())
    )
    for entry in all_sales_totals:
        all_customer_totals[entry['customer_id']] = {
            'sales': entry['total'] or Decimal('0')
        }
    
    # Get total payments for all customers in one query
    all_payment_totals = Payment.objects.filter(
        customer_id__in=customer_ids
    ).values('customer_id').annotate(
        total=Sum('amount')
    )
    for entry in all_payment_totals:
        customer_id = entry['customer_id']
        if customer_id not in all_customer_totals:
            all_customer_totals[customer_id] = {'sales': Decimal('0')}
        all_customer_totals[customer_id]['payments'] = entry['total'] or Decimal('0')
    
    # Calculate balances
    for customer_id, totals in all_customer_totals.items():
        sales_total = totals.get('sales', Decimal('0'))
        payment_total = totals.get('payments', Decimal('0'))
        all_customer_totals[customer_id]['balance'] = sales_total - payment_total
    
    # Pre-fetch all milk types for all customers in one query
    customer_milk_type_map = {}
    for customer in customers:
        customer_milk_type_map[customer.id] = list(customer.milk_types.all())
    
    # Get month's total amounts for each customer in one query
    month_total_amounts = {}
    monthly_sales_totals = Sale.objects.filter(
        customer_id__in=customer_ids,
        date__gte=start_date,
        date__lte=end_date
    ).values('customer_id').annotate(
        total_amount=Sum(F('quantity') * F('rate'), output_field=DecimalField())
    )
    for entry in monthly_sales_totals:
        month_total_amounts[entry['customer_id']] = entry['total_amount'] or Decimal('0')
    
    # Group sales data by customer and milk_type for easier lookup
    sales_by_customer_milk_type = {}
    for sale in all_sales:
        customer_id = sale.customer_id
        milk_type_id = sale.milk_type_id
        sale_date = sale.date
        
        if customer_id not in sales_by_customer_milk_type:
            sales_by_customer_milk_type[customer_id] = {}
        
        if milk_type_id not in sales_by_customer_milk_type[customer_id]:
            sales_by_customer_milk_type[customer_id][milk_type_id] = {}
        
        day = sale_date.day
        if day not in sales_by_customer_milk_type[customer_id][milk_type_id]:
            sales_by_customer_milk_type[customer_id][milk_type_id][day] = Decimal('0')
        
        sales_by_customer_milk_type[customer_id][milk_type_id][day] += sale.quantity
    
    # Process each customer
    customers_data = []
    
    for customer in customers:
        customer_id = customer.id
        balance = all_customer_totals.get(customer_id, {}).get('balance', Decimal('0'))
        total_amount = month_total_amounts.get(customer_id, Decimal('0'))
        
        # Get milk types used by this customer
        customer_milk_types = customer_milk_type_map.get(customer_id, [])
        
        # If customer has no milk types but has sales, use milk types from sales
        if not customer_milk_types and customer_id in sales_by_customer_milk_type:
            # Get unique milk types from sales
            milk_type_ids = sales_by_customer_milk_type[customer_id].keys()
            customer_milk_types = [Sale.objects.filter(id__in=list(all_sales)[:1], milk_type_id=mt_id).first().milk_type 
                                for mt_id in milk_type_ids]
        
        # Create milk type data for this customer
        milk_types_data = []
        
        for milk_type in customer_milk_types:
            if not milk_type:
                continue
            
            milk_type_id = milk_type.id
            daily_data = {}
            milk_type_quantity = Decimal('0')
            milk_type_amount = Decimal('0')
            
            # Get customer's sales data for this milk type
            if customer_id in sales_by_customer_milk_type and milk_type_id in sales_by_customer_milk_type[customer_id]:
                milk_type_sales = sales_by_customer_milk_type[customer_id][milk_type_id]
                
                # Process daily data
                for day in range(1, days_in_month + 1):
                    quantity = milk_type_sales.get(day, Decimal('0'))
                    daily_data[day] = quantity
                    milk_type_quantity += quantity
                
                # Calculate amount for this milk type
                milk_type_amount = milk_type_quantity * milk_type.rate_per_liter
            else:
                # Initialize empty daily data
                for day in range(1, days_in_month + 1):
                    daily_data[day] = Decimal('0')
            
            # Skip milk types with no sales if customer doesn't have a balance
            if milk_type_quantity == 0 and balance == 0:
                continue
                
            # Add milk type data
            milk_types_data.append({
                'milk_type': milk_type,
                'daily_data': daily_data,
                'total_quantity': milk_type_quantity,
                'total_amount': milk_type_amount
            })
        
        # Skip customer if they have no milk types with data
        if not milk_types_data and balance == 0:
            continue
            
        # Add customer data with milk types
        customers_data.append({
            'customer': customer,
            'balance': balance,
            'overall_total': total_amount,
            'milk_types': milk_types_data,
            'num_milk_types': len(milk_types_data)
        })
    
    # Generate month/year options for dropdown
    month_options = [
        {'number': m, 'name': datetime.date(2000, m, 1).strftime('%B')}
        for m in range(1, 13)
    ]
    
    current_year = today.year
    year_options = range(current_year - 2, current_year + 1)
    
    context = {
        'customers_data': customers_data,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'month_name': start_date.strftime('%B'),
        'month_options': month_options,
        'year_options': year_options,
        'day_range': day_range,
        'days_in_month': days_in_month,
        'preview_days': preview_days
    }
    
    return render(request, 'dairy_app/customer_export.html', context)


@login_required
def download_customer_data(request):
    """View for downloading customer data as Excel"""
    from django.utils.translation import gettext as _
    from django.utils.translation import get_language
    from django.utils.dates import MONTHS
    
    # Get parameters
    selected_month = int(request.GET.get('month', timezone.now().month))
    selected_year = int(request.GET.get('year', timezone.now().year))
    
    # Validate month and year
    today = timezone.now().date()
    if not 1 <= selected_month <= 12:
        selected_month = today.month
    if not 2000 <= selected_year <= 2100:
        selected_year = today.year
    
    # Generate start and end dates for the selected month
    start_date = datetime.date(selected_year, selected_month, 1)
    if selected_month == 12:
        end_date = datetime.date(selected_year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(selected_year, selected_month + 1, 1) - datetime.timedelta(days=1)
    
    days_in_month = end_date.day
    
    # Get all customers
    customers = Customer.objects.all().order_by('name')
    
    # Create filename with translated month name
    month_name = _(start_date.strftime('%B'))
    filename = f"customer_data_{month_name}_{selected_year}"
    
    # For Excel export
    import xlwt
    
    # Create workbook and add sheet
    wb = xlwt.Workbook(encoding='utf-8')
    sheet_name = _('Customer Data')
    ws = wb.add_sheet(sheet_name[:31])  # Excel sheet names limited to 31 chars
    
    # Define borders - all thin
    borders = xlwt.Borders()
    borders.left = xlwt.Borders.THIN
    borders.right = xlwt.Borders.THIN
    borders.top = xlwt.Borders.THIN
    borders.bottom = xlwt.Borders.THIN
    
    # Styles
    header_style = xlwt.easyxf('font: bold on; align: wrap on, vert centre, horiz center')
    header_style.borders = borders
    
    date_style = xlwt.easyxf('font: bold on; align: wrap on, vert centre, horiz center')
    date_style.borders = borders
    
    # Customer name style - center aligned
    customer_style = xlwt.easyxf('align: wrap on, vert centre, horiz center')
    customer_style.borders = borders
    
    # Regular cell style with borders
    cell_style = xlwt.easyxf('align: wrap on')
    cell_style.borders = borders
    
    # Number style with right alignment and borders
    number_style = xlwt.easyxf('align: wrap on, horiz right')
    number_style.num_format_str = '0.00'
    number_style.borders = borders
    
    # Balance and overall total style - middle aligned
    amount_style = xlwt.easyxf('font: bold on; align: wrap on, vert centre, horiz center')
    amount_style.num_format_str = '0.00'
    amount_style.borders = borders
    
    # Total style
    total_style = xlwt.easyxf('font: bold on; align: wrap on, horiz right')
    total_style.num_format_str = '0.00'
    total_style.borders = borders
    
    # Translate column headers
    customer_header = _('Customer')
    milk_type_header = _('Milk Type')
    total_liters_header = _('Total (L)')
    total_amount_header = _('Total Amount (₹)')
    balance_header = _('Balance (₹)')
    overall_total_header = _('Overall Total (₹)')
    
    # Write headers
    col_idx = 0
    ws.write(0, col_idx, customer_header, header_style)
    col_idx += 1
    ws.write(0, col_idx, milk_type_header, header_style)
    col_idx += 1
    
    # Days headers (just the day number)
    daily_delivery_header = _('Daily Milk Delivery (liters)')
    for day in range(1, days_in_month + 1):
        ws.write(0, col_idx, str(day), date_style)
        col_idx += 1
    
    # Total columns
    ws.write(0, col_idx, total_liters_header, header_style)
    col_idx += 1
    ws.write(0, col_idx, total_amount_header, header_style)
    col_idx += 1
    ws.write(0, col_idx, balance_header, header_style)
    col_idx += 1
    ws.write(0, col_idx, overall_total_header, header_style)
    
    # Process each customer and write data
    row_idx = 1
    
    for customer in customers:
        # Calculate customer's overall balance
        total_sales_all_time = Sale.objects.filter(customer=customer).aggregate(
            total=Sum(F('quantity') * F('rate'), output_field=DecimalField())
        )['total'] or Decimal('0')
        
        total_payments = Payment.objects.filter(customer=customer).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        balance = total_sales_all_time - total_payments
        
        # Get sales for this customer in the selected month
        sales = Sale.objects.filter(
            customer=customer,
            date__gte=start_date,
            date__lte=end_date
        ).select_related('milk_type')
        
        if not sales.exists() and balance == 0:
            continue  # Skip customers with no sales in selected month and zero balance
        
        # Calculate customer's total amount for this month
        total_amount = sales.aggregate(
            total=Sum(F('quantity') * F('rate'), output_field=DecimalField())
        )['total'] or Decimal('0')
        
        # Get milk types used by this customer
        customer_milk_types = list(customer.milk_types.all())
        
        # If customer has no milk types but has sales, use milk types from sales
        if not customer_milk_types:
            customer_milk_types = list(set(sale.milk_type for sale in sales))
        
        # If there are no sales and no milk types associated, just show one row with balance
        if not customer_milk_types and not sales.exists() and balance != 0:
            # Write customer name
            col_idx = 0
            ws.write(row_idx, col_idx, customer.name, customer_style)
            col_idx += 1
            ws.write(row_idx, col_idx, "-", cell_style)
            col_idx += 1
            
            # Skip all days (empty)
            for _ in range(days_in_month):
                ws.write(row_idx, col_idx, '-', cell_style)
                col_idx += 1
            
            # Write empty totals
            ws.write(row_idx, col_idx, 0, number_style)
            col_idx += 1
            ws.write(row_idx, col_idx, 0, number_style)
            col_idx += 1
            
            # Write balance
            ws.write(row_idx, col_idx, float(balance), amount_style)
            col_idx += 1
            
            # Write overall total
            ws.write(row_idx, col_idx, float(total_amount), amount_style)
            
            row_idx += 1
            continue
        
        first_row_for_customer = row_idx
        customer_rows_count = len([mt for mt in customer_milk_types if 
                                  sales.filter(milk_type=mt).exists() or balance != 0])
        
        # If no milk types have sales, ensure at least one row
        if customer_rows_count == 0:
            customer_rows_count = 1
        
        # If this customer has multiple milk types, merge cells for customer name, balance and overall total first
        if customer_rows_count > 1:
            # Merge customer name column
            ws.write_merge(first_row_for_customer, first_row_for_customer + customer_rows_count - 1, 0, 0, customer.name, customer_style)
            
            # Calculate column indices for balance and overall total
            balance_col = 2 + days_in_month + 2  # Customer, Milk Type, Days columns, Total L, Total Amount
            overall_total_col = balance_col + 1
            
            # Merge balance and overall total columns
            ws.write_merge(first_row_for_customer, first_row_for_customer + customer_rows_count - 1, 
                           balance_col, balance_col, float(balance), amount_style)
            ws.write_merge(first_row_for_customer, first_row_for_customer + customer_rows_count - 1, 
                           overall_total_col, overall_total_col, float(total_amount), amount_style)
        else:
            # Only one milk type, no need to merge
            ws.write(first_row_for_customer, 0, customer.name, customer_style)
            
            balance_col = 2 + days_in_month + 2
            overall_total_col = balance_col + 1
            
            ws.write(first_row_for_customer, balance_col, float(balance), amount_style)
            ws.write(first_row_for_customer, overall_total_col, float(total_amount), amount_style)
        
        # Process each milk type
        current_row = first_row_for_customer
        for milk_type in customer_milk_types:
            # Get sales for this specific milk type
            milk_type_sales = sales.filter(milk_type=milk_type)
            
            # Calculate totals for this milk type
            milk_type_quantity = milk_type_sales.aggregate(total=Sum('quantity'))['total'] or Decimal('0')
            milk_type_amount = milk_type_sales.aggregate(
                total=Sum(F('quantity') * F('rate'), output_field=DecimalField())
            )['total'] or Decimal('0')
            
            # Skip milk types with no sales if they don't have a balance
            if milk_type_quantity == 0 and balance == 0:
                continue
            
            # Write milk type name (column 1)
            ws.write(current_row, 1, milk_type.name, cell_style)
            
            # Write daily quantities for this milk type
            col_idx = 2  # Start from the first day column
            for day in range(1, days_in_month + 1):
                day_date = datetime.date(selected_year, selected_month, day)
                day_sales = milk_type_sales.filter(date=day_date)
                quantity = day_sales.aggregate(total=Sum('quantity'))['total'] or Decimal('0')
                
                if quantity > 0:
                    ws.write(current_row, col_idx, float(quantity), number_style)
                else:
                    ws.write(current_row, col_idx, '-', cell_style)
                col_idx += 1
            
            # Write milk type total quantity
            ws.write(current_row, col_idx, float(milk_type_quantity), number_style)
            col_idx += 1
            
            # Write milk type total amount
            ws.write(current_row, col_idx, float(milk_type_amount), number_style)
            
            current_row += 1
        
        # Update the row_idx to the next available row
        row_idx = current_row
    
    # Set column width
    col_count = 2 + days_in_month + 3  # Customer, Milk type, Days, Total L, Total Amount, Balance, Overall Total
    for i in range(col_count):
        if i == 0:  # Customer name column
            ws.col(i).width = 256 * 30  # 30 characters wide
        elif i == 1:  # Milk type column
            ws.col(i).width = 256 * 10  # 10 characters wide
        elif i <= 1 + days_in_month:  # Day columns
            ws.col(i).width = 256 * 5   # 5 characters wide
        else:
            ws.col(i).width = 256 * 15  # 15 characters wide
    
    # Create response with correct MIME type for Excel files

@login_required
def generate_customer_bill(request, pk):
    """Generate a PDF bill for a specific customer using a template PDF"""
    import os
    from django.conf import settings
    from PyPDF2 import PdfReader, PdfWriter
    from reportlab.lib.units import inch, cm
    from reportlab.pdfgen import canvas
    
    customer = get_object_or_404(Customer, pk=pk)
    
    # Get the month and year parameters, default to current month if not provided
    today = timezone.now().date()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    
    # Get the start and end date for the selected month
    start_date = datetime.date(year, month, 1)
    # Find the last day of month
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime.date(year, month + 1, 1) - timedelta(days=1)
    
    # Get sales for this customer in the selected month
    sales = Sale.objects.filter(
        customer=customer,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date', 'milk_type__name')
    
    # Get payments for this customer in the selected month
    payments = Payment.objects.filter(
        customer=customer,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    # Calculate totals
    total_amount = sales.aggregate(
        total=Sum(F('quantity') * F('rate'), output_field=DecimalField())
    )['total'] or Decimal('0')
    
    total_payment = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Calculate previous balance (before this month)
    previous_sales = Sale.objects.filter(
        customer=customer,
        date__lt=start_date
    ).aggregate(
        total=Sum(F('quantity') * F('rate'), output_field=DecimalField())
    )['total'] or Decimal('0')
    
    previous_payments = Payment.objects.filter(
        customer=customer,
        date__lt=start_date
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    previous_balance = previous_sales - previous_payments
    
    # Calculate current balance
    current_balance = previous_balance + total_amount - total_payment
    
    # Group sales by milk type
    milk_type_summary = {}
    for sale in sales:
        milk_type_name = sale.milk_type.name
        if milk_type_name not in milk_type_summary:
            milk_type_summary[milk_type_name] = {
                'quantity': Decimal('0'),
                'amount': Decimal('0'),
                'rate': sale.rate
            }
        milk_type_summary[milk_type_name]['quantity'] += sale.quantity
        milk_type_summary[milk_type_name]['amount'] += sale.quantity * sale.rate
    
    # Path to the PDF template - using the provided template
    template_path = os.path.join(settings.BASE_DIR, 'Dairy_bill1.pdf')
    
    # Check if template exists
    if not os.path.exists(template_path):
        # If template doesn't exist, return an error
        messages.error(request, "Bill template not found. Please ensure 'Dairy_bill1.pdf' is in the project root directory.")
        return redirect('customer_detail', pk=pk)
    
    # Create a buffer for our data layer
    data_buffer = BytesIO()
    
    # Register Devanagari font - make sure this font exists in your system
    # Let's check for different possible font locations and use a fallback mechanism
    font_paths = [
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'NotoSansDevanagari-VariableFont_wdth,wght.ttf'),
        os.path.join(settings.BASE_DIR, 'fonts', 'NotoSansDevanagari-VariableFont_wdth,wght.ttf'),
        # Add fallback fonts that support Devanagari
        'Arial Unicode MS',
        'NotoSansDevanagari-Regular',
        'Mangal',
    ]
    
    # Try to register a Devanagari-compatible font
    devanagari_font_registered = False
    for font_path in font_paths:
        try:
            # For file paths
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('DevanagariFont', font_path))
                devanagari_font_registered = True
                break
            # For system fonts (just try to register by name)
            elif not os.path.sep in font_path:
                try:
                    pdfmetrics.registerFont(TTFont('DevanagariFont', font_path))
                    devanagari_font_registered = True
                    break
                except:
                    pass
        except:
            continue
    
    # Create a PDF to add data on
    c = canvas.Canvas(data_buffer, pagesize=A4)
    width, height = A4  # A4 size in points
    
    # Get month name and translate it
    from django.utils.dates import MONTHS
    month_name = str(_(MONTHS[month]))
    
    # Adjust coordinates to match your provided template (Dairy Bill.pdf)
    # These coordinates may need adjustment based on the exact layout of your template
    
    # Customer Information Section
    # Use Devanagari font if registered, otherwise fallback to Helvetica
    font_name = "DevanagariFont" if devanagari_font_registered else "Helvetica-Bold"
    
    c.setFont(font_name, 15)
    c.drawString(2.3*cm, height-7.75*cm, f"{customer.name}")
    
    # Add month and year
    c.setFont(font_name, 15)
    c.drawString(width-7.5*cm, height-7.75*cm, f"{month_name}")
    
    c.setFont(font_name, 15)
    c.drawString(width-3.7*cm, height-7.75*cm, f"{year}")

    # Adjust these coordinates to match your provided template (Dairy Bill.pdf)
    # Table headers
    y_position = height - 12.5*cm
    table_left = 2.9*cm
    
  
    
    # Add milk consumption data
    y_position -= 1.5*cm
    c.setFont(font_name if devanagari_font_registered else "Helvetica", 12)
    
    # Maximum rows we can fit in the table area
    max_rows = 5
    row_count = 0
    
    for milk_type, details in milk_type_summary.items():
        if row_count >= max_rows:
            break  # Don't overflow the template
            
        # Use the milk_type name directly without translation
        c.drawString(table_left, y_position, milk_type)
        c.drawString(table_left + 5.3*cm, y_position, f"{details['rate']:.2f}")
        c.drawString(table_left + 9.1*cm, y_position, f"{details['quantity']:.2f}")
        c.drawString(table_left + 13.9*cm, y_position, f"{details['amount']:.2f}")
        
        y_position -= 1.6*cm
        row_count += 1
    
    # Add total line at the bottom of the table
    if milk_type_summary:  # Only if there are items
        c.setFont(font_name if devanagari_font_registered else "Helvetica-Bold", 13)
        c.drawString(table_left, height-18.6*cm, str(_("Total")))
        c.drawString(table_left + 9.1*cm, height-18.6*cm, 
                    f"{sum(item['quantity'] for item in milk_type_summary.values()):.2f}")
        c.drawString(table_left + 13.9*cm, height-18.6*cm, f"{total_amount:.2f}")
    
    # Payment summary section
    payment_y = height - 20.3*cm
    payment_left = 1.5*cm
    payment_value_left = width - 4.25*cm
    
    c.setFont(font_name if devanagari_font_registered else "Helvetica", 13)
    c.drawString(payment_left, payment_y, f"{str(_('Previous Balance'))}")
    c.drawString(payment_value_left, payment_y, f"{previous_balance:.2f}")
    payment_y -= 1.5*cm
    
    c.drawString(payment_left, payment_y, f"{str(_('Current Month Total'))}")
    c.drawString(payment_value_left, payment_y, f"{total_amount:.2f}")
    payment_y -= 1.5*cm
    
    c.drawString(payment_left, payment_y, f"{str(_('Payments Received'))}")
    c.drawString(payment_value_left, payment_y, f"{total_payment:.2f}")
    
    # Final balance
    balance_y = height - 25*cm
    c.setFont(font_name if devanagari_font_registered else "Helvetica-Bold", 13)
    c.drawString(payment_left, balance_y, str(_("Balance Due:")))
    c.drawString(payment_value_left, balance_y, f"{current_balance:.2f}")


    
    # Add generation info
    c.setFont(font_name if devanagari_font_registered else "Helvetica", 8)
    c.drawRightString(width-2*cm, 0.5*cm, f"{str(_('Generated on'))}: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    
    # Save the data layer PDF
    c.save()
    
    # Get the value of the BytesIO buffer
    data_buffer.seek(0)
    
    # Create a new PDF with PdfWriter
    output_buffer = BytesIO()
    
    # Read the template PDF
    template_pdf = PdfReader(open(template_path, "rb"))
    output_pdf = PdfWriter()
    
    # Read the data layer PDF
    data_pdf = PdfReader(data_buffer)
    
    # Get both pages from template PDF (assuming it has 2 pages)
    template_page1 = template_pdf.pages[0]
    template_page2 = template_pdf.pages[1] if len(template_pdf.pages) > 1 else None
    data_page = data_pdf.pages[0]
    
    # Merge the data onto the first template page
    template_page1.merge_page(data_page)
    
    # Add the merged first page to the output PDF
    output_pdf.add_page(template_page1)
    
    # Create a data layer for the second page with day-wise milk distribution table
    second_page_buffer = BytesIO()
    p2 = canvas.Canvas(second_page_buffer, pagesize=A4)
    p2_width, p2_height = A4  # A4 size in points
    

    
    # Add customer name, month and year
    p2.setFont(font_name if devanagari_font_registered else "Helvetica-Bold", 14)
    p2.drawString(2*cm, p2_height-3.5*cm, f"{str(_('Customer'))}: {customer.name}")
    p2.drawString(2*cm, p2_height-4.5*cm, f"{str(_('Month'))}: {month_name} {year}")
    
    # Calculate days in the selected month
    days_in_month = (end_date - start_date).days + 1
    
    # Create day-wise data structure for milk deliveries
    daily_milk_data = {}
    
    # Populate the daily data from sales
    for sale in sales:
        day = sale.date.day
        if day not in daily_milk_data:
            daily_milk_data[day] = {}
        
        milk_type_name = sale.milk_type.name
        if milk_type_name not in daily_milk_data[day]:
            daily_milk_data[day][milk_type_name] = 0
            
        daily_milk_data[day][milk_type_name] += sale.quantity
    
    # Get unique milk types from sales
    unique_milk_types = set()
    for day_data in daily_milk_data.values():
        for milk_type in day_data.keys():
            unique_milk_types.add(milk_type)
    unique_milk_types = sorted(list(unique_milk_types))
    
    # Draw the table
    table_top = p2_height - 6*cm
    table_left = 2*cm
    row_height = 0.8*cm
    col_width = 1.5*cm
    date_col_width = 2*cm
    milk_type_col_width = 3*cm
    
    # Calculate table dimensions based on content
    table_width = date_col_width + len(unique_milk_types) * col_width
    
    # Draw table header
    p2.setFont(font_name if devanagari_font_registered else "Helvetica-Bold", 12)
    p2.drawString(table_left, table_top, str(_("Day")))
    
    # Draw milk type column headers
    milk_type_x = table_left + date_col_width
    for milk_type in unique_milk_types:
        p2.drawString(milk_type_x, table_top, milk_type)
        milk_type_x += col_width
    
    # Draw horizontal line below header
    p2.line(table_left, table_top - 0.3*cm, table_left + table_width, table_top - 0.3*cm)
    
    # Set up for 2-column layout with fixed 15 days per column
    # Define column offsets
    column_offset = p2_width / 2  # Divide the page in half
    
    # First column will always have 15 days, second column the remainder
    days_in_first_column = 15
    
    # Draw the day rows
    column = 0
    page = 1
    row_y = table_top - row_height
    
    # Draw headers for both columns at the start
    for col in range(2):
        col_left = table_left + col * column_offset
        
        p2.setFont(font_name if devanagari_font_registered else "Helvetica-Bold", 12)
        p2.drawString(col_left, table_top, str(_("Day")))
        
        milk_type_x = col_left + date_col_width
        for milk_type in unique_milk_types:
            p2.drawString(milk_type_x, table_top, milk_type)
            milk_type_x += col_width
        
        p2.line(col_left, table_top - 0.3*cm, col_left + table_width, table_top - 0.3*cm)
    
    for day in range(1, days_in_month + 1):
        # Determine which column this day belongs to
        if day <= days_in_first_column:
            column = 0
            # Maintain vertical position relative to the first day in column
            row_y = table_top - row_height - ((day - 1) * row_height)
        else:
            column = 1
            # Maintain vertical position relative to the first day in column
            row_y = table_top - row_height - ((day - days_in_first_column - 1) * row_height)
            
        # Calculate current column's left position
        current_left = table_left + column * column_offset
        
        # Draw day number
        p2.setFont(font_name if devanagari_font_registered else "Helvetica", 12)
        p2.drawString(current_left, row_y, str(day))
        
        # Draw milk quantities for each type
        milk_type_x = current_left + date_col_width
        for milk_type in unique_milk_types:
            quantity = 0
            if day in daily_milk_data and milk_type in daily_milk_data[day]:
                quantity = daily_milk_data[day][milk_type]
            
            if quantity > 0:
                p2.drawString(milk_type_x, row_y, f"{quantity:.2f}")
            milk_type_x += col_width
        
        row_y -= row_height
    
    
    # Save the second page data layer
    p2.save()
    second_page_buffer.seek(0)
    
    # Read the second page data layer
    second_page_pdf = PdfReader(second_page_buffer)
    second_page_data = second_page_pdf.pages[0]
    
    # If template has a second page, merge with it, otherwise add the new page directly
    if template_page2:
        template_page2.merge_page(second_page_data)
        output_pdf.add_page(template_page2)
    else:
        output_pdf.add_page(second_page_data)
    
    # Write the output PDF to the buffer
    output_pdf.write(output_buffer)
    output_buffer.seek(0)
    
    # Create the HttpResponse object with PDF content
    response = HttpResponse(content_type='application/pdf')
    file_name = f"Bill_{customer.name}_{month_name}_{year}.pdf".replace(" ", "_")
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    
    # Write the merged PDF to the response
    response.write(output_buffer.getvalue())
    
    # Clean up buffers
    data_buffer.close()
    output_buffer.close()
    
    return response
    response = HttpResponse(content_type='application/vnd.ms-excel')
    
    # Set the Content-Disposition header with proper filename and extension
    sanitized_filename = filename.replace(" ", "_")  # Replace spaces with underscores
    response['Content-Disposition'] = f'attachment; filename="{sanitized_filename}.xls"'
    
    # Save workbook to response
    wb.save(response)
    return response


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import TruncDay
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _

# Import ReportLab for PDF generation conditionally
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.units import cm, inch, mm
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from io import BytesIO
import os
import tempfile

# Import PyPDF2 conditionally
try:
    from PyPDF2 import PdfReader, PdfWriter
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

from django.conf import settings

from .models import MilkType, Customer, Sale, Payment, Area, MonthlyBalance
from .forms import (
    MilkTypeForm, CustomerForm, SaleForm, 
    SaleInputForm, PaymentForm,
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
    
    # Get areas count - show all areas for superusers, only own areas for regular users
    if request.user.is_superuser:
        areas_count = Area.objects.all().count()
    else:
        areas_count = Area.objects.filter(user=request.user).count()
    
    context = {
        'customers_count': customers_count,
        'areas_count': areas_count,
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
        # Search for customers by name, ordered by delivery order within area, then creation time for milk distribution route
        customers = Customer.objects.filter(name__icontains=search_query).order_by('area', 'delivery_order', 'date_joined')[:10]  # Limit to 10 results
        
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
        # Show all areas for superusers, only own areas for regular users
        if self.request.user.is_superuser:
            return Area.objects.all()
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
        # Allow superusers to edit all areas, regular users only their own
        if self.request.user.is_superuser:
            return Area.objects.all()
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
        # Allow superusers to delete all areas, regular users only their own
        if self.request.user.is_superuser:
            return Area.objects.all()
        return Area.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        area = self.get_object()
        messages.success(request, f"Area '{area.name}' deleted successfully!")
        return super().delete(request, *args, **kwargs)


@login_required
def area_customers_view(request, pk):
    """View customers for a specific area"""
    # Allow superusers to access all areas, regular users only their own
    if request.user.is_superuser:
        area = get_object_or_404(Area, pk=pk)
    else:
        area = get_object_or_404(Area, pk=pk, user=request.user)
    
    # Order by delivery_order, then by date_joined for new customers without order
    customers = Customer.objects.filter(area=area).order_by('delivery_order', 'date_joined')
    
    context = {
        'area': area,
        'customers': customers
    }
    
    return render(request, 'dairy_app/area_customers.html', context)


@login_required
def update_customer_order(request):
    """AJAX view to update customer delivery order"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            customer_ids = data.get('customer_ids', [])
            area_id = data.get('area_id')
            
            # Verify area ownership for non-superusers
            if not request.user.is_superuser:
                area = get_object_or_404(Area, pk=area_id, user=request.user)
            else:
                area = get_object_or_404(Area, pk=area_id)
            
            # Update delivery order for each customer
            for index, customer_id in enumerate(customer_ids):
                Customer.objects.filter(
                    id=customer_id, 
                    area=area
                ).update(delivery_order=index + 1)
            
            return JsonResponse({'success': True, 'message': 'Customer order updated successfully'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


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
        area_filtered = False
        if area_id:
            try:
                queryset = queryset.filter(area_id=area_id)
                area_filtered = True
            except ValueError:
                pass
                
        # Filter by search term
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            # More comprehensive search across name field
            queryset = queryset.filter(name__icontains=search_query)
        
        # Order by delivery order within area when filtering by area (for milk distribution route),
        # otherwise order by name for general browsing
        if area_filtered:
            return queryset.order_by('delivery_order', 'date_joined')  # Milk distribution route order
        else:
            return queryset.order_by('name')  # Alphabetical for general browsing
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current date
        today = timezone.now().date()
        
        # Get search query for highlighting
        search_query = self.request.GET.get('search', '').strip()
        
        # Highlight customer names if there's a search query
        if search_query:
            for customer in context['customers']:
                customer.highlighted_name = self.highlight_text(customer.name, search_query)
        
        # Add areas for filtering - show all areas for superusers, only own areas for regular users
        if self.request.user.is_superuser:
            areas = Area.objects.all()
        else:
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
                
                # Highlight the customer name if there's a search query
                customer_name = customer.name
                highlighted_name = self.highlight_text(customer_name, search_query) if search_query else customer_name
                
                # Create row
                row = {
                    'counter': idx + 1,
                    'id': customer.id,
                    'name': customer_name,
                    'highlighted_name': highlighted_name,
                    'milk_types_html': milk_types_html
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
        
        # Get all monthly balances - show last 6 months
        context['monthly_balances'] = MonthlyBalance.objects.filter(
            customer=customer
        ).order_by('-year', '-month')[:6]  # Show last 6 months
        
        # Get last 6 months status with detailed information
        context['last_six_months_status'] = customer.get_last_six_months_status()
        
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
        
        # Add navigation for previous/next customer in the same area
        if customer.area:
            # Get customers in the same area, ordered by creation time (milk distribution route order)
            area_customers = Customer.objects.filter(
                area=customer.area
            ).order_by('delivery_order', 'date_joined')
            
            # Convert to list to find current customer's position
            customer_list = list(area_customers)
            
            try:
                current_index = customer_list.index(customer)
                
                # Get previous customer
                if current_index > 0:
                    context['previous_customer'] = customer_list[current_index - 1]
                else:
                    context['previous_customer'] = None
                
                # Get next customer
                if current_index < len(customer_list) - 1:
                    context['next_customer'] = customer_list[current_index + 1]
                else:
                    context['next_customer'] = None
                
                # Add area navigation info
                context['area_customer_position'] = current_index + 1
                context['area_total_customers'] = len(customer_list)
                context['area_name'] = customer.area.name
                
            except ValueError:
                # Customer not found in area (shouldn't happen, but handle gracefully)
                context['previous_customer'] = None
                context['next_customer'] = None
                context['area_customer_position'] = 1
                context['area_total_customers'] = 1
        else:
            # If customer has no area, get all customers without area ordered by creation time
            no_area_customers = Customer.objects.filter(
                area__isnull=True
            ).order_by('delivery_order', 'date_joined')
            
            customer_list = list(no_area_customers)
            
            try:
                current_index = customer_list.index(customer)
                
                # Get previous customer
                if current_index > 0:
                    context['previous_customer'] = customer_list[current_index - 1]
                else:
                    context['previous_customer'] = None
                
                # Get next customer
                if current_index < len(customer_list) - 1:
                    context['next_customer'] = customer_list[current_index + 1]
                else:
                    context['next_customer'] = None
                
                # Add navigation info for no-area customers
                context['area_customer_position'] = current_index + 1
                context['area_total_customers'] = len(customer_list)
                context['area_name'] = 'Unassigned'
                
            except ValueError:
                # Customer not found (shouldn't happen)
                context['previous_customer'] = None
                context['next_customer'] = None
                context['area_customer_position'] = 1
                context['area_total_customers'] = 1
        
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
    
    def get_initial(self):
        """Pre-fill the area field if coming from an area page"""
        initial = super().get_initial()
        
        # Check if area parameter is provided in URL
        area_id = self.request.GET.get('area')
        if area_id:
            try:
                # Verify the area exists and belongs to the user (or user is superuser)
                if self.request.user.is_superuser:
                    area = Area.objects.get(id=area_id)
                else:
                    area = Area.objects.get(id=area_id, user=self.request.user)
                initial['area'] = area
            except (Area.DoesNotExist, ValueError):
                # If area doesn't exist or doesn't belong to user, ignore
                pass
        
        return initial
    
    def get_context_data(self, **kwargs):
        """Add area context for display purposes"""
        context = super().get_context_data(**kwargs)
        
        # Check if area parameter is provided in URL for context
        area_id = self.request.GET.get('area')
        if area_id:
            try:
                # Verify the area exists and belongs to the user (or user is superuser)
                if self.request.user.is_superuser:
                    area = Area.objects.get(id=area_id)
                else:
                    area = Area.objects.get(id=area_id, user=self.request.user)
                context['selected_area'] = area
                context['from_area_page'] = True
            except (Area.DoesNotExist, ValueError):
                # If area doesn't exist or doesn't belong to user, ignore
                context['from_area_page'] = False
        else:
            context['from_area_page'] = False
        
        return context
    
    def get_success_url(self):
        """Redirect to area customers page if coming from an area, otherwise to customer list"""
        area_id = self.request.GET.get('area')
        if area_id:
            try:
                # Verify the area exists and belongs to the user (or user is superuser)
                if self.request.user.is_superuser:
                    Area.objects.get(id=area_id)
                else:
                    Area.objects.get(id=area_id, user=self.request.user)
                return reverse_lazy('area_customers', kwargs={'pk': area_id})
            except (Area.DoesNotExist, ValueError):
                # If area doesn't exist or doesn't belong to user, use default
                pass
        
        return reverse_lazy('customer_list')
    
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
    
    # Handle customer selection
    customer_id = request.GET.get('customer')
    last_sale_quantities = {}
    
    # If customer ID is provided, get the customer
    if customer_id:
        try:
            customer = Customer.objects.get(id=customer_id)
            customer_milk_types = customer.milk_types.all()
            from_customer_page = True  # Always treat as from customer page when customer is specified
            
            # Get the last sale quantity for each milk type for this customer
            for milk_type in customer_milk_types:
                last_sale = Sale.objects.filter(
                    customer=customer, 
                    milk_type=milk_type
                ).order_by('-created_at').first()
                
                if last_sale:
                    last_sale_quantities[milk_type.id] = last_sale.quantity
            
            form = SaleForm(initial={'customer': customer}, customer_fixed=True)
        except Customer.DoesNotExist:
            form = SaleForm()
    else:
        # If no customer specified, redirect to customer list to select one
        if not request.GET.get('search'):
            return redirect('customer_list')
        form = SaleForm()
    
    # Handle search query (only if no customer is already selected)
    if not customer:
        search_query = request.GET.get('search', '').strip()
        if search_query:
            search_results = Customer.objects.filter(name__icontains=search_query).order_by('area', 'delivery_order', 'date_joined')

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
            customer_fixed = customer is not None
            form = SaleForm(request.POST, customer_fixed=customer_fixed)
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
                
                # Redirect back to customer detail if coming from customer page
                if customer:
                    return redirect('customer_detail', pk=customer.id)
                else:
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
    
    # Handle customer selection
    customer_id = request.GET.get('customer')
    fetch_unpaid = request.GET.get('fetch_unpaid') == 'true'
    return_to = request.GET.get('return', '')
    
    # Check if user is coming from customer detail page
    # First check if return parameter is provided (most reliable)
    if return_to == 'customer_detail':
        from_customer_page = True
    elif customer_id:
        # If customer parameter is provided, likely from customer page
        from_customer_page = True
    else:
        # Fallback to referer check
        referer = request.META.get('HTTP_REFERER', '')
        from_customer_page = '/customers/' in referer
    
    # If no customer selected and not from customer page, redirect to customer list with search
    if not customer_id and not from_customer_page:
        return redirect('customer_list')
    
    # Handle search query
    search_query = request.GET.get('search', '').strip()
    if search_query:
        search_results = Customer.objects.filter(name__icontains=search_query).order_by('date_joined')  # Order by route sequence
    
    if customer_id:
        try:
            customer = Customer.objects.get(id=customer_id)
            form = PaymentForm(initial={'customer': customer}, customer_fixed=from_customer_page)
            
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
        form = PaymentForm(request.POST, customer_fixed=customer is not None)
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
            
            # Check return preference - prioritize return parameter, then other indicators
            return_to = request.POST.get('return', request.GET.get('return', ''))
            
            # If coming from customer detail page, redirect back there
            if (return_to == 'customer_detail' or from_customer_page) and payment.customer:
                return redirect('customer_detail', pk=payment.customer.id)
            return redirect('payment_list')
    
    context = {
        'form': form,
        'customer': customer,
        'from_customer_page': from_customer_page,
        'search_results': search_results,
        'return_to': return_to,
    }
    
    return render(request, 'dairy_app/payment_form.html', context)


class PaymentUpdateView(LoginRequiredMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'dairy_app/payment_form.html'
    
    def get_queryset(self):
        # Return all payments
        return Payment.objects.all()
    
    def get(self, request, *args, **kwargs):
        """Handle GET requests, including AJAX requests for unpaid months."""
        self.object = self.get_object()
        
        # Handle AJAX request for fetching unpaid months
        fetch_unpaid = request.GET.get('fetch_unpaid') == 'true'
        customer_id = request.GET.get('customer')
        
        if fetch_unpaid and 'HTTP_X_REQUESTED_WITH' in request.META and customer_id:
            try:
                from .models import Customer, MonthlyBalance
                customer = Customer.objects.get(id=customer_id)
                form = PaymentForm(instance=self.object, initial={'customer': customer})
                
                # Force recalculation first for accurate data
                MonthlyBalance.update_monthly_balances(customer)
                
                # For editing payments, we need to include months that are currently allocated to this payment
                unpaid_months = form.get_unpaid_months(customer)
                
                # Also get months that are currently allocated to this payment
                try:
                    from django.apps import apps
                    PaymentAllocation = apps.get_model('dairy_app', 'PaymentAllocation')
                    current_allocations = PaymentAllocation.objects.filter(payment=self.object)
                    
                    # Get monthly balances for months allocated to this payment
                    for allocation in current_allocations:
                        try:
                            balance = MonthlyBalance.objects.get(
                                customer=customer,
                                year=allocation.year,
                                month=allocation.month
                            )
                            
                            # Check if this month is not already in unpaid_months
                            month_already_included = any(
                                month['month'] == allocation.month and month['year'] == allocation.year 
                                for month in unpaid_months
                            )
                            
                            if not month_already_included:
                                # Add this month to the list as it's currently allocated to this payment
                                from calendar import month_name
                                month_data = {
                                    'month': allocation.month,
                                    'year': allocation.year,
                                    'sales_amount': balance.sales_amount,
                                    'payment_amount': balance.payment_amount - allocation.amount,  # Subtract current allocation
                                    'remaining': balance.sales_amount - (balance.payment_amount - allocation.amount),
                                    'month_name': month_name[allocation.month],
                                    'is_currently_allocated': True  # Mark this for UI indication
                                }
                                unpaid_months.append(month_data)
                        except MonthlyBalance.DoesNotExist:
                            continue
                    
                    # Sort the combined list by year and month (newest first)
                    unpaid_months.sort(key=lambda x: (x['year'], x['month']), reverse=True)
                    
                except ImportError:
                    # PaymentAllocation model may not be available
                    pass
                
                form.unpaid_months = unpaid_months
                
                # Render the partial template with just the unpaid months
                return render(request, 'dairy_app/payment_form_partial.html', {
                    'form': form,
                    'customer': customer
                })
            except Customer.DoesNotExist:
                pass
        
        # Default behavior for non-AJAX requests
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add customer to context so the template doesn't redirect to search
        context['customer'] = self.object.customer
        
        # Check return preference
        return_to = self.request.GET.get('return', '')
        if return_to == 'customer_detail':
            context['from_customer_page'] = True
        else:
            # Check if we came from customer detail page via referer
            referer = self.request.META.get('HTTP_REFERER', '')
            context['from_customer_page'] = '/customers/' in referer
        
        context['return_to'] = return_to
        
        # Add unpaid months to the form for multi-month functionality
        from .models import MonthlyBalance
        if self.object.customer:
            MonthlyBalance.update_monthly_balances(self.object.customer)
            unpaid_months = context['form'].get_unpaid_months(self.object.customer)
            
            # For editing payments, also include months that are currently allocated to this payment
            try:
                from django.apps import apps
                PaymentAllocation = apps.get_model('dairy_app', 'PaymentAllocation')
                current_allocations = PaymentAllocation.objects.filter(payment=self.object)
                
                # Get monthly balances for months allocated to this payment
                for allocation in current_allocations:
                    try:
                        balance = MonthlyBalance.objects.get(
                            customer=self.object.customer,
                            year=allocation.year,
                            month=allocation.month
                        )
                        
                        # Check if this month is not already in unpaid_months
                        month_already_included = any(
                            month['month'] == allocation.month and month['year'] == allocation.year 
                            for month in unpaid_months
                        )
                        
                        if not month_already_included:
                            # Add this month to the list as it's currently allocated to this payment
                            from calendar import month_name
                            month_data = {
                                'month': allocation.month,
                                'year': allocation.year,
                                'sales_amount': balance.sales_amount,
                                'payment_amount': balance.payment_amount - allocation.amount,  # Subtract current allocation
                                'remaining': balance.sales_amount - (balance.payment_amount - allocation.amount),
                                'month_name': month_name[allocation.month],
                                'is_currently_allocated': True  # Mark this for UI indication
                            }
                            unpaid_months.append(month_data)
                    except MonthlyBalance.DoesNotExist:
                        continue
                
                # Sort the combined list by year and month (newest first)
                unpaid_months.sort(key=lambda x: (x['year'], x['month']), reverse=True)
                
            except ImportError:
                # PaymentAllocation model may not be available
                pass
            
            context['form'].unpaid_months = unpaid_months
        
        # Check if this payment has multi-month allocations
        from django.apps import apps
        try:
            PaymentAllocation = apps.get_model('dairy_app', 'PaymentAllocation')
            allocations = PaymentAllocation.objects.filter(payment=self.object)
            if allocations.exists():
                context['is_multi_month_payment'] = True
                context['existing_allocations'] = allocations
                # Mark as multi-month in the form
                context['form'].initial['is_multi_month'] = True
            else:
                context['is_multi_month_payment'] = False
        except:
            context['is_multi_month_payment'] = False
            
        return context
    
    def get_success_url(self):
        # Check return preference in both GET and POST
        return_to = self.request.POST.get('return', self.request.GET.get('return', ''))
        
        if return_to == 'customer_detail' and self.object.customer:
            return reverse_lazy('customer_detail', kwargs={'pk': self.object.customer.id})
        
        # Fallback to referer check
        referer = self.request.META.get('HTTP_REFERER', '')
        if '/customers/' in referer and self.object.customer:
            return reverse_lazy('customer_detail', kwargs={'pk': self.object.customer.id})
        
        return reverse_lazy('payment_list')
    
    def form_valid(self, form):
        # Handle multi-month allocation updates
        is_multi_month = form.cleaned_data.get('is_multi_month')
        
        if is_multi_month:
            # For multi-month payments, clear single-month assignment
            form.instance.payment_for_month = None
            form.instance.payment_for_year = None
        
        response = super().form_valid(form)
        
        # Handle multi-month allocation redistribution
        if is_multi_month and 'selected_months' in self.request.POST:
            # Process multiple month allocation similar to create view
            selected_month_strings = self.request.POST.getlist('selected_months')
            
            # Parse the selected months from format "month_year"
            selected_months = []
            for month_str in selected_month_strings:
                try:
                    month, year = month_str.split('_')
                    selected_months.append((int(month), int(year)))
                except (ValueError, IndexError):
                    continue
            
            if selected_months:
                # CRITICAL: When editing a payment, we must temporarily remove existing allocations
                # to get accurate unpaid amounts for redistribution calculation
                from .models import MonthlyBalance
                from django.apps import apps
                PaymentAllocation = apps.get_model('dairy_app', 'PaymentAllocation')
                current_allocations = PaymentAllocation.objects.filter(payment=self.object)
                
                # Store current allocations for potential restoration
                current_allocation_data = []
                for alloc in current_allocations:
                    current_allocation_data.append({
                        'month': alloc.month,
                        'year': alloc.year,
                        'amount': alloc.amount
                    })
                
                # Temporarily delete current allocations to get accurate unpaid amounts
                current_allocations.delete()
                
                # Update monthly balances to reflect the removal of current allocations
                MonthlyBalance.update_monthly_balances(self.object.customer)
                
                # Get all monthly balances (both previously paid and unpaid) for redistribution
                all_balances = MonthlyBalance.objects.filter(
                    customer=self.object.customer,
                    sales_amount__gt=0
                ).order_by('year', 'month')
                
                # Create new allocations based on selected months and available amounts
                allocations = []
                amount_remaining = self.object.amount
                
                for balance in all_balances:
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
                    
                    if amount_remaining <= 0:
                        break
                
                # Apply the new allocation distribution
                if allocations:
                    self.object.distribute_to_months(allocations)
                else:
                    # If no valid allocations could be created, restore original allocations
                    if current_allocation_data:
                        self.object.distribute_to_months(current_allocation_data)
        
        # Force recalculation of all monthly balances for this customer 
        # after saving the payment to ensure accurate balances
        customer = self.object.customer
        from .models import MonthlyBalance
        MonthlyBalance.update_monthly_balances(customer)
        
        messages.success(self.request, "Payment updated successfully!")
        return response


class PaymentDeleteView(LoginRequiredMixin, DeleteView):
    model = Payment
    template_name = 'dairy_app/payment_confirm_delete.html'
    
    def get_queryset(self):
        # Return all payments
        return Payment.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check return preference
        return_to = self.request.GET.get('return', '')
        context['return_to'] = return_to
        
        if return_to == 'customer_detail':
            context['from_customer_page'] = True
        else:
            # Check if we came from customer detail page via referer
            referer = self.request.META.get('HTTP_REFERER', '')
            context['from_customer_page'] = '/customers/' in referer
        
        return context
    
    def get_success_url(self):
        # Check return preference in both GET and POST
        return_to = self.request.POST.get('return', self.request.GET.get('return', ''))
        
        if return_to == 'customer_detail' and self.object.customer:
            return reverse_lazy('customer_detail', kwargs={'pk': self.object.customer.id})
        
        # Fallback to referer check
        referer = self.request.META.get('HTTP_REFERER', '')
        if '/customers/' in referer and self.object.customer:
            return reverse_lazy('customer_detail', kwargs={'pk': self.object.customer.id})
        
        return reverse_lazy('payment_list')
    
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
@login_required
def customer_export_view(request):
    """View for displaying customer data export page with month/year and area selection"""
    # Get current date
    today = timezone.now().date()
    
    # Handle month/year/area selection
    if request.method == 'POST':
        selected_month = int(request.POST.get('month', today.month))
        selected_year = int(request.POST.get('year', today.year))
        selected_area = request.POST.get('area', '')
    else:
        selected_month = int(request.GET.get('month', today.month))
        selected_year = int(request.GET.get('year', today.year))
        selected_area = request.GET.get('area', '')
    
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
    
    # Filter customers by area if specified, limit to top 25 for web view
    customers = Customer.objects.all().order_by('name')
    if selected_area:
        customers = customers.filter(area_id=selected_area)
    customers = customers[:25]
    
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
    
    # Get all areas for the dropdown
    areas = Area.objects.all().order_by('name')
    
    context = {
        'customers_data': customers_data,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'selected_area': selected_area,
        'month_name': start_date.strftime('%B'),
        'month_options': month_options,
        'year_options': year_options,
        'areas': areas,
        'day_range': day_range,
        'days_in_month': days_in_month,
        'preview_days': preview_days
    }
    
    return render(request, 'dairy_app/customer_export.html', context)


@login_required
def download_customer_data(request):
    """View for downloading customer data as Excel with area filtering"""
    from django.utils.translation import gettext as _
    from django.utils.translation import get_language
    from django.utils.dates import MONTHS
    
    # Get parameters
    selected_month = int(request.GET.get('month', timezone.now().month))
    selected_year = int(request.GET.get('year', timezone.now().year))
    selected_area = request.GET.get('area', '')  # Add area filter
    
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
    
    # Get customers filtered by area if specified
    customers = Customer.objects.all().order_by('name')
    if selected_area:
        customers = customers.filter(area_id=selected_area)
    
    # Create filename with translated month name and area
    month_name = _(start_date.strftime('%B'))
    area_suffix = ""
    if selected_area:
        try:
            area = Area.objects.get(id=selected_area)
            area_suffix = f"_{area.name}"
        except Area.DoesNotExist:
            pass
    
    filename = f"customer_data_{month_name}_{selected_year}{area_suffix}"
    
    # Check if xlwt is available
    try:
        import xlwt
    except ImportError:
        messages.error(request, "Excel export library (xlwt) not installed. Please contact administrator.")
        return redirect('customer_export')
    
    # For Excel export
    
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
    area_header = _('Area')
    milk_type_header = _('Milk Type')
    total_liters_header = _('Total (L)')
    total_amount_header = _('Total Amount (₹)')
    balance_header = _('Balance (₹)')
    overall_total_header = _('Overall Total (₹)')
    
    # Write headers
    col_idx = 0
    ws.write(0, col_idx, customer_header, header_style)
    col_idx += 1
    ws.write(0, col_idx, area_header, header_style)
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
            # Write area
            ws.write(row_idx, col_idx, customer.area.name if customer.area else "-", cell_style)
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
        
        # If this customer has multiple milk types, merge cells for customer name, area, balance and overall total first
        if customer_rows_count > 1:
            # Merge customer name column
            ws.write_merge(first_row_for_customer, first_row_for_customer + customer_rows_count - 1, 0, 0, customer.name, customer_style)
            
            # Merge area column
            area_name = customer.area.name if customer.area else "-"
            ws.write_merge(first_row_for_customer, first_row_for_customer + customer_rows_count - 1, 1, 1, area_name, customer_style)
            
            # Calculate column indices for balance and overall total
            balance_col = 3 + days_in_month + 2  # Customer, Area, Milk Type, Days columns, Total L, Total Amount
            overall_total_col = balance_col + 1
            
            # Merge balance and overall total columns
            ws.write_merge(first_row_for_customer, first_row_for_customer + customer_rows_count - 1, 
                           balance_col, balance_col, float(balance), amount_style)
            ws.write_merge(first_row_for_customer, first_row_for_customer + customer_rows_count - 1, 
                           overall_total_col, overall_total_col, float(total_amount), amount_style)
        else:
            # Only one milk type, no need to merge
            ws.write(first_row_for_customer, 0, customer.name, customer_style)
            ws.write(first_row_for_customer, 1, customer.area.name if customer.area else "-", customer_style)
            
            balance_col = 3 + days_in_month + 2
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
            
            # Write milk type name (column 2)
            ws.write(current_row, 2, milk_type.name, cell_style)
            
            # Write daily quantities for this milk type
            col_idx = 3  # Start from the first day column (after customer, area, milk type)
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
    col_count = 3 + days_in_month + 3  # Customer, Area, Milk type, Days, Total L, Total Amount, Balance, Overall Total
    for i in range(col_count):
        if i == 0:  # Customer name column
            ws.col(i).width = 256 * 30  # 30 characters wide
        elif i == 1:  # Area column
            ws.col(i).width = 256 * 15  # 15 characters wide
        elif i == 2:  # Milk type column
            ws.col(i).width = 256 * 10  # 10 characters wide
        elif i <= 2 + days_in_month:  # Day columns
            ws.col(i).width = 256 * 5   # 5 characters wide
        else:
            ws.col(i).width = 256 * 15  # 15 characters wide
    
    # Create response with correct MIME type for Excel files
    response = HttpResponse(content_type='application/vnd.ms-excel')
    
    # Set the Content-Disposition header with proper filename and extension
    sanitized_filename = filename.replace(" ", "_")  # Replace spaces with underscores
    response['Content-Disposition'] = f'attachment; filename="{sanitized_filename}.xls"'
    
    # Save workbook to response
    wb.save(response)
    return response

@login_required
def generate_customer_bill(request, pk):
    """Generate a PDF bill for a specific customer using a template PDF"""
    import os
    from django.conf import settings
    
    # Check if reportlab is available
    if not REPORTLAB_AVAILABLE:
        messages.error(request, _('PDF generation is not available. ReportLab is not installed.'))
        return redirect('customer_detail', pk=pk)
        
    from reportlab.lib.units import inch, cm
    from reportlab.pdfgen import canvas
    
    # Check if PyPDF2 is available
    if not PYPDF2_AVAILABLE:
        messages.error(request, _('PDF generation is not available. PyPDF2 is not installed.'))
        return redirect('customer_detail', pk=pk)
    
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
    template_path = os.path.join(settings.BASE_DIR, 'new_bill.pdf')
    
    # Check if template exists
    if not os.path.exists(template_path):
        # If template doesn't exist, return an error
        messages.error(request, "Bill template not found. Please ensure 'new_bill.pdf' is in the project root directory.")
        return redirect('customer_detail', pk=pk)
    
    # Check if reportlab is available
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from io import BytesIO
    except ImportError as e:
        messages.error(request, f"PDF generation libraries not installed: {e}")
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
    p2.drawString(2*cm, p2_height-1.2*cm, f"{str(_('Customer'))}: {customer.name}")
    p2.drawString(2*cm, p2_height-2.0*cm, f"{str(_('Month'))}: {month_name} {year}")
    
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
    
    # Draw the table with exact template dimensions - adjusted positioning
    table_top = p2_height - 2.8*cm  # Shifted down by 0.5cm
    table_left = 1.01*cm + 0.76*cm              # Shifted right by 0.2cm
    table_bottom = table_top - 17.12*cm        # Exact table height from template
    table_right = table_left + 18.98*cm        # Exact table width from template
    
    # Calculate precise dimensions for 8 columns × 16 rows grid
    total_rows = 16
    total_cols = 8
    
    # Calculate row height and column width to fit exactly in the grid
    table_height = table_top - table_bottom
    table_width = table_right - table_left
    
    row_height = table_height / total_rows  # Precise row height
    col_width = table_width / total_cols    # Precise column width
    
    # Layout: 2 halves of 4 columns each
    # Left half: Day + 3 milk types (columns 1-4) for days 1-16
    # Right half: Day + 3 milk types (columns 5-8) for days 17-31
    cols_per_half = 4
    milk_types_per_half = 3  # 3 milk types per half (excluding day column)
    
    # Limit milk types to fit in available space (max 3 milk types displayed)
    displayed_milk_types = list(unique_milk_types)[:milk_types_per_half]
    
    # Draw headers for both halves
    p2.setFont(font_name if devanagari_font_registered else "Helvetica-Bold", 10)
    
    # Left half headers (columns 1-4)
    left_day_x = table_left
    p2.drawString(left_day_x, table_top, str(_("Day")))
    
    milk_type_x = left_day_x + col_width
    for milk_type in displayed_milk_types:
        # Truncate long milk type names to fit in column
        display_name = milk_type[:8] if len(milk_type) > 8 else milk_type
        # Set bold font for milk type headers
        p2.setFont(font_name if devanagari_font_registered else "Helvetica-Bold", 10)
        p2.drawString(milk_type_x, table_top, display_name)
        milk_type_x += col_width
    
    # Right half headers (columns 5-8)
    right_day_x = table_left + (cols_per_half * col_width)
    p2.drawString(right_day_x, table_top, str(_("Day")))
    
    milk_type_x = right_day_x + col_width
    for milk_type in displayed_milk_types:
        # Truncate long milk type names to fit in column
        display_name = milk_type[:8] if len(milk_type) > 8 else milk_type
        # Set bold font for milk type headers
        p2.setFont(font_name if devanagari_font_registered else "Helvetica-Bold", 10)
        p2.drawString(milk_type_x, table_top, display_name)
        milk_type_x += col_width
    

    
    # Draw the day rows with 2-column layout
    # Left half: days 1-15 (reserve 1 row for header, 15 rows for data)
    # Right half: days 16-31
    max_days_left = 15  # Days 1-15 in left half
    
    # Draw left half data (days 1-15)
    row_y = table_top - row_height  # Start below header
    
    for day in range(1, min(days_in_month + 1, max_days_left + 1)):
        # Draw day number in first column (left half)
        p2.setFont(font_name if devanagari_font_registered else "Helvetica", 10)
        p2.drawString(left_day_x, row_y, str(day))
        
        # Draw milk quantities for each type in left half
        milk_type_x = left_day_x + col_width
        for milk_type in displayed_milk_types:
            quantity = 0
            if day in daily_milk_data and milk_type in daily_milk_data[day]:
                quantity = daily_milk_data[day][milk_type]
            
            if quantity > 0:
                p2.drawString(milk_type_x, row_y, f"{quantity:.1f}")
            else:
                p2.drawString(milk_type_x, row_y, "-")
            milk_type_x += col_width
        
        row_y -= row_height
    
    # Draw right half data (days 16-31)
    row_y = table_top - row_height  # Reset to start below header
    
    for day in range(max_days_left + 1, days_in_month + 1):
        # Draw day number in fifth column (right half)
        p2.setFont(font_name if devanagari_font_registered else "Helvetica", 10)
        p2.drawString(right_day_x, row_y, str(day))
        
        # Draw milk quantities for each type in right half
        milk_type_x = right_day_x + col_width
        for milk_type in displayed_milk_types:
            quantity = 0
            if day in daily_milk_data and milk_type in daily_milk_data[day]:
                quantity = daily_milk_data[day][milk_type]
            
            if quantity > 0:
                p2.drawString(milk_type_x, row_y, f"{quantity:.1f}")
            else:
                p2.drawString(milk_type_x, row_y, "-")
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


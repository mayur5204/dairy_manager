#!/usr/bin/env python
"""
Debug script to identify why unpaid months are taking too long to load.
"""

import os
import sys
import django
import time

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dairy_manager.settings')
django.setup()

from dairy_app.models import Customer, MonthlyBalance, Sale
from dairy_app.forms import PaymentForm

def debug_unpaid_months():
    """Debug the unpaid months loading issue."""
    
    print("🔍 Debugging unpaid months loading issue...")
    
    try:
        # Get a customer with data
        customer = Customer.objects.first()
        if not customer:
            print("❌ No customers found in database")
            return
            
        print(f"📝 Testing with customer: {customer.name}")
        
        # Check sales data range
        sales = Sale.objects.filter(customer=customer)
        sales_count = sales.count()
        print(f"📊 Customer has {sales_count} sales records")
        
        if sales.exists():
            earliest = sales.order_by('date').first().date
            latest = sales.order_by('date').last().date
            print(f"📅 Sales range: {earliest} to {latest}")
            
            # Calculate the number of months this covers
            years_diff = latest.year - earliest.year
            months_diff = (years_diff * 12) + (latest.month - earliest.month) + 1
            print(f"⏱️  This covers approximately {months_diff} months")
            
            if months_diff > 50:
                print("⚠️  WARNING: Large date range detected! This could cause performance issues.")
        
        # Test the MonthlyBalance.update_monthly_balances method
        print("\n🔄 Testing MonthlyBalance.update_monthly_balances...")
        start_time = time.time()
        MonthlyBalance.update_monthly_balances(customer)
        update_time = time.time() - start_time
        print(f"⏱️  MonthlyBalance update took {update_time:.2f} seconds")
        
        if update_time > 5:
            print("⚠️  WARNING: MonthlyBalance update is slow!")
        
        # Test the get_unpaid_months method
        print("\n🔄 Testing PaymentForm.get_unpaid_months...")
        form = PaymentForm()
        start_time = time.time()
        unpaid_months = form.get_unpaid_months(customer)
        unpaid_time = time.time() - start_time
        print(f"⏱️  get_unpaid_months took {unpaid_time:.2f} seconds")
        print(f"📊 Found {len(unpaid_months)} unpaid months")
        
        if unpaid_time > 5:
            print("⚠️  WARNING: get_unpaid_months is slow!")
        
        # Show the unpaid months
        if unpaid_months:
            print("\n📋 Unpaid months:")
            for month in unpaid_months[:5]:  # Show first 5
                print(f"   {month['month_name']} {month['year']}: ₹{month['remaining']:.2f} remaining")
            if len(unpaid_months) > 5:
                print(f"   ... and {len(unpaid_months) - 5} more")
        
        # Check existing monthly balances
        monthly_balances = MonthlyBalance.objects.filter(customer=customer)
        print(f"\n📊 Customer has {monthly_balances.count()} monthly balance records")
        
        unpaid_balances = monthly_balances.filter(is_paid=False, sales_amount__gt=0)
        print(f"📊 {unpaid_balances.count()} are unpaid with sales > 0")
        
        print("\n✅ Debug completed successfully!")
        
    except Exception as e:
        print(f"❌ Debug failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_unpaid_months()

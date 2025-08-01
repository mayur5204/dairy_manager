#!/usr/bin/env python
import os
import django
import sys

# Add the project path
sys.path.append(r'c:\Users\mayur\OneDrive\Desktop\dairy_manager\dairy_manager')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dairy_manager.settings')
django.setup()

from dairy_app.models import Customer, PaymentAllocation
from decimal import Decimal

# Test the calculation for a customer with multi-month payment allocation
try:
    # Get a customer (you may need to adjust this to match your customer)
    customer = Customer.objects.first()  # or Customer.objects.get(name="Your Customer Name")
    
    if customer:
        print(f"Testing customer: {customer.name}")
        print("=" * 50)
        
        # Test July 2025 specifically
        year, month = 2025, 7
        
        # Get month balance info
        balance_info = customer.get_month_balance(year, month)
        
        print(f"July {year} calculation:")
        print(f"  Sales Total: {balance_info['sales_total']}")
        print(f"  Payment Total: {balance_info['payment_total']}")
        print(f"  Month Balance: {balance_info['month_balance']}")
        
        # Check payment allocations directly
        try:
            allocations = PaymentAllocation.objects.filter(
                payment__customer=customer,
                month=month,
                year=year
            )
            print(f"  Payment Allocations for July 2025:")
            for alloc in allocations:
                print(f"    - ₹{alloc.amount} from payment ID {alloc.payment.id} dated {alloc.payment.date}")
        except Exception as e:
            print(f"  Error checking allocations: {e}")
        
        # Test the status logic
        sales_amount = balance_info['sales_total']
        payment_amount = balance_info['payment_total']
        balance = balance_info['month_balance']
        
        print(f"\nStatus Logic Test:")
        print(f"  sales_amount == 0: {sales_amount == 0}")
        print(f"  balance <= 0: {balance <= 0}")
        print(f"  payment_amount > 0: {payment_amount > 0}")
        
        if sales_amount == 0:
            status = 'no_sales'
        elif balance <= 0:
            status = 'paid'
        elif payment_amount > 0:
            status = 'partial'
        else:
            status = 'pending'
            
        print(f"  Calculated Status: {status}")
        
        # Also test the actual method
        months_data = customer.get_last_six_months_status()
        july_data = None
        for month_data in months_data:
            if month_data['year'] == 2025 and month_data['month'] == 7:
                july_data = month_data
                break
        
        if july_data:
            print(f"\nActual Method Result for July 2025:")
            print(f"  Sales: {july_data['sales_amount']}")
            print(f"  Payments: {july_data['payment_amount']}")
            print(f"  Balance: {july_data['balance']}")
            print(f"  Status: {july_data['status']}")
            print(f"  Debug Info: {july_data.get('debug_info', 'N/A')}")
    else:
        print("No customer found")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

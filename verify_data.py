#!/usr/bin/env python
"""
Quick verification script to show current database state.
"""

import os
import sys
import django

# Set up Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dairy_manager.settings')
django.setup()

from dairy_app.models import Customer, Sale, MonthlyBalance
from decimal import Decimal

def show_current_state():
    """Show current database state."""
    print("🔍 Current Database State")
    print("=" * 50)
    
    # Count totals
    total_customers = Customer.objects.count()
    june_sales = Sale.objects.filter(date__year=2025, date__month=6).count()
    july_sales = Sale.objects.filter(date__year=2025, date__month=7).count()
    
    print(f"📊 Summary:")
    print(f"  - Total Customers: {total_customers}")
    print(f"  - June 2025 Sales: {june_sales}")
    print(f"  - July 2025 Sales: {july_sales}")
    print(f"  - Total Sales: {june_sales + july_sales}")
    
    # Show monthly balance status
    june_balances = MonthlyBalance.objects.filter(year=2025, month=6)
    july_balances = MonthlyBalance.objects.filter(year=2025, month=7)
    
    june_unpaid_count = june_balances.filter(is_paid=False).count()
    july_unpaid_count = july_balances.filter(is_paid=False).count()
    
    june_total_unpaid = sum(
        balance.sales_amount - balance.payment_amount 
        for balance in june_balances 
        if not balance.is_paid
    )
    
    july_total_unpaid = sum(
        balance.sales_amount - balance.payment_amount 
        for balance in july_balances 
        if not balance.is_paid
    )
    
    print(f"\n💰 Payment Status:")
    print(f"  June 2025:")
    print(f"    - Unpaid customers: {june_unpaid_count}/{june_balances.count()}")
    print(f"    - Total unpaid amount: ₹{june_total_unpaid:.2f}")
    print(f"  July 2025:")
    print(f"    - Unpaid customers: {july_unpaid_count}/{july_balances.count()}")
    print(f"    - Total unpaid amount: ₹{july_total_unpaid:.2f}")
    print(f"  Overall unpaid: ₹{june_total_unpaid + july_total_unpaid:.2f}")
    
    # Show sample customer data
    print(f"\n👥 Sample Customer Data (first 5 customers):")
    for customer in Customer.objects.all()[:5]:
        june_balance = june_balances.filter(customer=customer).first()
        july_balance = july_balances.filter(customer=customer).first()
        
        june_amount = june_balance.sales_amount if june_balance else Decimal('0')
        july_amount = july_balance.sales_amount if july_balance else Decimal('0')
        
        print(f"  {customer.name}:")
        print(f"    - June: ₹{june_amount:.2f} ({'UNPAID' if june_balance and not june_balance.is_paid else 'PAID'})")
        print(f"    - July: ₹{july_amount:.2f} ({'UNPAID' if july_balance and not july_balance.is_paid else 'PAID'})")
    
    print(f"\n✅ Database is ready for testing multi-month payments!")
    print(f"🎯 You can now test the payment system with customers who have unpaid amounts for both June and July 2025.")

if __name__ == "__main__":
    show_current_state()

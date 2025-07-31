#!/usr/bin/env python
"""
Test script to verify that multi-month payment allocation 
correctly updates the pending status of monthly balances.
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dairy_manager.settings')
django.setup()

from dairy_app.models import Customer, Payment, PaymentAllocation, MonthlyBalance, Sale, MilkType
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, datetime

def test_multi_month_payment_status():
    """Test that multi-month payments properly update pending status."""
    
    print("Testing multi-month payment status updates...")
    
    try:
        # Get a customer and user
        customer = Customer.objects.first()
        user = User.objects.first()
        
        if not customer or not user:
            print("No customer or user found in database")
            return
            
        print(f"Using customer: {customer.name}")
        
        # Create some test sales for different months to ensure we have unpaid balances
        milk_type = MilkType.objects.first()
        if not milk_type:
            print("No milk type found in database")
            return
            
        # Create sales for January, February, March 2025
        test_sales = []
        for month in [1, 2, 3]:
            sale = Sale.objects.create(
                user=user,
                customer=customer,
                milk_type=milk_type,
                date=date(2025, month, 15),  # Mid-month
                quantity=Decimal('10.00'),  # 10 liters
                rate=Decimal('50.00')       # ₹50 per liter
            )
            test_sales.append(sale)
            print(f"Created sale for {month}/2025: ₹{sale.total_amount()}")
        
        # Update monthly balances to reflect the new sales
        MonthlyBalance.update_monthly_balances(customer)
        
        # Check initial status - should all be unpaid
        print("\nInitial monthly balance status:")
        for month in [1, 2, 3]:
            balance = MonthlyBalance.objects.get(customer=customer, year=2025, month=month)
            print(f"  {month}/2025: Sales=₹{balance.sales_amount}, Payments=₹{balance.payment_amount}, Paid={balance.is_paid}")
        
        # Create a multi-month payment of ₹1000 to cover January and February (₹500 each)
        payment = Payment.objects.create(
            customer=customer,
            user=user,
            amount=Decimal('1000.00'),
            date=date.today(),
            description="Multi-month test payment"
        )
        
        print(f"\nCreated payment: ₹{payment.amount}")
        
        # Distribute the payment across January and February
        month_allocations = [
            {'month': 1, 'year': 2025, 'amount': Decimal('500.00')},
            {'month': 2, 'year': 2025, 'amount': Decimal('500.00')},
        ]
        
        allocations = payment.distribute_to_months(month_allocations)
        print(f"Created {len(allocations)} payment allocations:")
        for alloc in allocations:
            print(f"  {alloc.month}/{alloc.year}: ₹{alloc.amount}")
        
        # Check the updated status - January and February should now be paid
        print("\nUpdated monthly balance status after payment allocation:")
        for month in [1, 2, 3]:
            # Force recalculation
            balance = MonthlyBalance.objects.get(customer=customer, year=2025, month=month)
            balance.recalculate()
            
            print(f"  {month}/2025: Sales=₹{balance.sales_amount}, Payments=₹{balance.payment_amount}, Paid={balance.is_paid}")
            
            # Verify the expected status
            if month <= 2:
                if balance.is_paid:
                    print(f"    ✅ Month {month} correctly marked as PAID")
                else:
                    print(f"    ❌ Month {month} should be PAID but is still PENDING")
            else:
                if not balance.is_paid:
                    print(f"    ✅ Month {month} correctly marked as PENDING")
                else:
                    print(f"    ❌ Month {month} should be PENDING but is marked as PAID")
        
        # Clean up test data
        print("\nCleaning up test data...")
        payment.delete()  # This should also delete allocations due to CASCADE
        for sale in test_sales:
            sale.delete()
        
        # Clean up monthly balances for these months
        MonthlyBalance.objects.filter(customer=customer, year=2025, month__in=[1, 2, 3]).delete()
        
        print("✅ Multi-month payment status test completed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_multi_month_payment_status()

#!/usr/bin/env python
"""
Test script to verify that payment distribution functionality works correctly
after fixing the PaymentAllocation import issue.
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dairy_manager.settings')
django.setup()

from dairy_app.models import Customer, Payment, PaymentAllocation
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date

def test_payment_distribution():
    """Test that payment distribution works without import errors."""
    
    print("Testing payment distribution functionality...")
    
    try:
        # Get a customer (or create one if none exists)
        customer = Customer.objects.first()
        if not customer:
            print("No customers found in the database.")
            return
        
        # Get a user (or create one if none exists)
        user = User.objects.first()
        if not user:
            print("No users found in the database.")
            return
            
        print(f"Using customer: {customer.name}")
        print(f"Using user: {user.username}")
        
        # Create a test payment
        payment = Payment(
            customer=customer,
            user=user,
            amount=Decimal('1000.00'),
            date=date.today(),
            description="Test payment for distribution"
        )
        payment.save()
        
        print(f"Created payment with ID: {payment.id}, Amount: ₹{payment.amount}")
        
        # Test the distribute_to_months method
        month_allocations = [
            {'month': 1, 'year': 2025, 'amount': Decimal('400.00')},
            {'month': 2, 'year': 2025, 'amount': Decimal('300.00')},
            {'month': 3, 'year': 2025, 'amount': Decimal('300.00')},
        ]
        
        # Call the distribute_to_months method
        allocations = payment.distribute_to_months(month_allocations)
        
        print(f"Successfully created {len(allocations)} payment allocations:")
        for allocation in allocations:
            print(f"  - {allocation.month}/{allocation.year}: ₹{allocation.amount}")
        
        # Verify the allocations were created in the database
        db_allocations = PaymentAllocation.objects.filter(payment=payment)
        print(f"Database contains {db_allocations.count()} allocations for this payment")
        
        # Clean up the test data
        payment.delete()
        print("Test payment deleted successfully")
        
        print("✅ Payment distribution test passed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_payment_distribution()

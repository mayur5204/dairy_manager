#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dairy_manager.settings')
django.setup()

from dairy_app.models import Customer

print("Available customers:")
print("=" * 30)

customers = Customer.objects.all()
for customer in customers:
    print(f"ID: {customer.id}, Name: {customer.name}")

if customers.exists():
    first_customer = customers.first()
    print(f"\nTesting with customer ID {first_customer.id} ({first_customer.name})...")
    print("=" * 60)
    
    statuses = first_customer.get_last_six_months_status()
    
    for month_data in statuses:
        print(f"Month: {month_data['month']}")
        print(f"  Status: {month_data['status']}")
        print(f"  Amount: {month_data['payment_amount']}")
        print(f"  Date: {month_data['payment_date']}")
        print("-" * 40)
    
    print("\nTest completed successfully! ✅")
else:
    print("No customers found in the database.")

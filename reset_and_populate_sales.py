#!/usr/bin/env python
"""
Script to reset database and populate with sales data for June and July 2025.
This will:
1. Remove all existing sales and payment data
2. Clean up monthly balances and payment allocations
3. Generate realistic sales data for June and July 2025
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
import random

def clear_existing_data():
    """Remove all existing sales, payments, and related data."""
    print("🗑️  Clearing existing data...")
    
    # Delete in the correct order to avoid foreign key constraints
    deleted_counts = {}
    
    # Delete payment allocations first
    deleted_counts['PaymentAllocation'] = PaymentAllocation.objects.all().delete()[0]
    
    # Delete payments
    deleted_counts['Payment'] = Payment.objects.all().delete()[0]
    
    # Delete sales
    deleted_counts['Sale'] = Sale.objects.all().delete()[0]
    
    # Delete monthly balances
    deleted_counts['MonthlyBalance'] = MonthlyBalance.objects.all().delete()[0]
    
    print("Deleted records:")
    for model, count in deleted_counts.items():
        print(f"  - {model}: {count} records")
    
    print("✅ Database cleared successfully!")

def generate_sales_data():
    """Generate realistic sales data for June and July 2025."""
    print("\n📊 Generating sales data for June and July 2025...")
    
    # Get required objects
    customers = list(Customer.objects.all())
    milk_types = list(MilkType.objects.all())
    user = User.objects.first()
    
    if not customers:
        print("❌ No customers found in database. Please add customers first.")
        return
    
    if not milk_types:
        print("❌ No milk types found in database. Please add milk types first.")
        return
        
    if not user:
        print("❌ No users found in database. Please add a user first.")
        return
    
    print(f"Found {len(customers)} customers and {len(milk_types)} milk types")
    
    # Generate sales for June and July 2025
    months_data = [
        {'year': 2025, 'month': 6, 'name': 'June'},
        {'year': 2025, 'month': 7, 'name': 'July'}
    ]
    
    total_sales_created = 0
    
    for month_info in months_data:
        year = month_info['year']
        month = month_info['month']
        month_name = month_info['name']
        
        print(f"\n📅 Creating sales for {month_name} {year}...")
        
        # Determine days in month
        if month == 6:  # June
            days_in_month = 30
        else:  # July
            days_in_month = 31
        
        month_sales_count = 0
        
        # Create sales for each customer
        for customer in customers:
            # Each customer gets sales on random days throughout the month
            # Most customers get 15-25 deliveries per month
            num_deliveries = random.randint(15, 25)
            
            # Generate random delivery days
            delivery_days = sorted(random.sample(range(1, days_in_month + 1), num_deliveries))
            
            customer_sales = []
            
            for day in delivery_days:
                # Random milk type for this customer (they might get different types)
                milk_type = random.choice(milk_types)
                
                # Random quantity between 0.5 to 3.0 liters
                quantity = Decimal(str(round(random.uniform(0.5, 3.0), 2)))
                
                # Use the milk type's rate
                rate = milk_type.rate_per_liter
                
                # Create the sale
                sale = Sale.objects.create(
                    user=user,
                    customer=customer,
                    milk_type=milk_type,
                    date=date(year, month, day),
                    quantity=quantity,
                    rate=rate,
                    notes=f"Daily delivery - {month_name} {year}"
                )
                
                customer_sales.append(sale)
                month_sales_count += 1
            
            # Calculate total for this customer this month
            customer_total = sum(sale.total_amount() for sale in customer_sales)
            print(f"  {customer.name}: {len(customer_sales)} deliveries, Total: ₹{customer_total:.2f}")
        
        print(f"✅ Created {month_sales_count} sales records for {month_name} {year}")
        total_sales_created += month_sales_count
    
    print(f"\n🎉 Successfully created {total_sales_created} total sales records!")
    
    # Update monthly balances for all customers
    print("\n🔄 Updating monthly balances...")
    for customer in customers:
        MonthlyBalance.update_monthly_balances(customer)
    
    print("✅ Monthly balances updated!")

def show_summary():
    """Show a summary of the generated data."""
    print("\n📋 Data Summary:")
    print("=" * 50)
    
    # Sales summary
    june_sales = Sale.objects.filter(date__year=2025, date__month=6)
    july_sales = Sale.objects.filter(date__year=2025, date__month=7)
    
    june_total = sum(sale.total_amount() for sale in june_sales)
    july_total = sum(sale.total_amount() for sale in july_sales)
    
    print(f"June 2025 Sales:")
    print(f"  - Records: {june_sales.count()}")
    print(f"  - Total Amount: ₹{june_total:.2f}")
    
    print(f"\nJuly 2025 Sales:")
    print(f"  - Records: {july_sales.count()}")
    print(f"  - Total Amount: ₹{july_total:.2f}")
    
    print(f"\nOverall Total: ₹{june_total + july_total:.2f}")
    
    # Monthly balances summary
    june_balances = MonthlyBalance.objects.filter(year=2025, month=6)
    july_balances = MonthlyBalance.objects.filter(year=2025, month=7)
    
    print(f"\nMonthly Balance Records:")
    print(f"  - June 2025: {june_balances.count()} customers")
    print(f"  - July 2025: {july_balances.count()} customers")
    
    # Show unpaid amounts
    june_unpaid = sum(balance.sales_amount - balance.payment_amount 
                     for balance in june_balances 
                     if not balance.is_paid)
    july_unpaid = sum(balance.sales_amount - balance.payment_amount 
                     for balance in july_balances 
                     if not balance.is_paid)
    
    print(f"\nUnpaid Amounts:")
    print(f"  - June 2025: ₹{june_unpaid:.2f}")
    print(f"  - July 2025: ₹{july_unpaid:.2f}")
    print(f"  - Total Unpaid: ₹{june_unpaid + july_unpaid:.2f}")

def main():
    """Main function to execute the data reset and generation."""
    print("🚀 Starting database reset and sales data generation...")
    print("=" * 60)
    
    try:
        # Step 1: Clear existing data
        clear_existing_data()
        
        # Step 2: Generate new sales data
        generate_sales_data()
        
        # Step 3: Show summary
        show_summary()
        
        print("\n" + "=" * 60)
        print("🎉 Database reset and sales generation completed successfully!")
        print("\nNext steps:")
        print("1. You can now test the payment system with fresh data")
        print("2. All customers have unpaid amounts for June and July 2025")
        print("3. Use the multi-month payment feature to test functionality")
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

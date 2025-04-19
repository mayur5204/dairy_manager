#!/usr/bin/env python
import os
import sys
import random
import django
import datetime
from decimal import Decimal
from faker import Faker
import string
import argparse

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dairy_manager.settings')
django.setup()

# Import models after setting up Django
from django.contrib.auth.models import User
from dairy_app.models import Customer, MilkType, Sale, Payment
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, F, DecimalField

def generate_phone():
    """Generate a random 10-digit phone number"""
    return ''.join(random.choices(string.digits, k=10))

def run(year=2025, month=3, num_customers=100, seed=None):
    """
    Delete all existing data and create new customer records with sales
    
    Args:
        year: The year to generate data for (default: 2025)
        month: The month to generate data for (default: 3 for March)
        num_customers: Number of customers to generate (default: 100)
        seed: Random seed for reproducible results (default: None)
    """
    # Set random seed if provided
    if seed is not None:
        random.seed(seed)
        if hasattr(Faker, 'seed'):
            Faker.seed(seed)
    
    month_name = datetime.date(year, month, 1).strftime('%B')
    print(f"Starting {month_name} {year} data refresh with {num_customers} customers...")

    # Get admin user or create one if it doesn't exist
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("No admin user found. Creating a new superuser...")
        admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin123"
        )
        print("Created admin user: admin/admin123")

    # Generate start and end dates for selected month
    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        
    days_in_month = (end_date - start_date).days + 1
    
    print(f"Refreshing data for {start_date.strftime('%B %Y')} ({days_in_month} days)")

    # Delete all existing data
    with transaction.atomic():
        print("Deleting all existing sales...")
        deleted_sales = Sale.objects.all().delete()[0]
        print(f"Deleted {deleted_sales} sales records.")
        
        print("Deleting all existing payments...")
        deleted_payments = Payment.objects.all().delete()[0]
        print(f"Deleted {deleted_payments} payment records.")
        
        print("Deleting all existing customers...")
        deleted_customers = Customer.objects.all().delete()[0]
        print(f"Deleted {deleted_customers} customer records.")
        
        print("Deleting all existing milk types...")
        deleted_milktypes = MilkType.objects.all().delete()[0]
        print(f"Deleted {deleted_milktypes} milk type records.")

        # Create milk types
        print("Creating milk types...")
        cow_milk = MilkType.objects.create(name="COW", rate_per_liter=Decimal("50.00"))
        gold_milk = MilkType.objects.create(name="GOLD", rate_per_liter=Decimal("70.00"))
        print("Created COW and GOLD milk types.")

        # Create customers with Faker
        print(f"Creating {num_customers} new customers...")
        fake = Faker('en_IN')  # Indian locale for realistic Indian names
        customers = []
        
        for i in range(num_customers):
            # Generate customer data
            name = fake.name()
            address = fake.address().replace('\n', ', ')
            phone = generate_phone()
            
            # Create customer
            customer = Customer.objects.create(
                user=admin_user,  # Associate with the admin user
                name=name,
                address=address,
                phone=phone
            )
            
            # Randomly assign milk types to customer
            milk_type_choice = random.choice([1, 2, 3])  # 1=COW, 2=GOLD, 3=BOTH
            
            if milk_type_choice in [1, 3]:  # COW or BOTH
                customer.milk_types.add(cow_milk)
                
            if milk_type_choice in [2, 3]:  # GOLD or BOTH
                customer.milk_types.add(gold_milk)
                
            customers.append(customer)
            
        print(f"Created {len(customers)} new customers.")

    # Assign customer patterns
    customer_patterns = {}
    
    for customer in customers:
        pattern = random.random()
        
        # Based on milk types the customer subscribes to
        customer_milk_types = list(customer.milk_types.all())
        
        if not customer_milk_types:
            continue  # Skip if customer has no milk types
            
        # Assign a pattern based on their subscription and randomness
        if len(customer_milk_types) == 1:
            milk_type = customer_milk_types[0]
            if milk_type.name == "COW":
                # Regular COW drinker (1L daily) - 70% of COW subscribers
                if pattern < 0.7:
                    customer_patterns[customer.id] = {
                        "type": "regular_cow",
                        "skip_probability": random.uniform(0.05, 0.15)  # 5-15% chance to skip a day
                    }
                # Irregular COW drinker - 30% of COW subscribers
                else:
                    customer_patterns[customer.id] = {
                        "type": "irregular_cow",
                        "skip_probability": random.uniform(0.2, 0.4)  # 20-40% chance to skip a day
                    }
            else:  # GOLD milk
                # Regular GOLD drinker (1L daily) - 80% of GOLD subscribers
                if pattern < 0.8:
                    customer_patterns[customer.id] = {
                        "type": "regular_gold",
                        "skip_probability": random.uniform(0.05, 0.10)  # 5-10% chance to skip a day
                    }
                # Irregular GOLD drinker - 20% of GOLD subscribers
                else:
                    customer_patterns[customer.id] = {
                        "type": "irregular_gold",
                        "skip_probability": random.uniform(0.15, 0.3)  # 15-30% chance to skip a day
                    }
        else:  # Customer has both milk types
            # Both types regular (1L GOLD, 0.5L COW) - 60% of dual subscribers
            if pattern < 0.6:
                customer_patterns[customer.id] = {
                    "type": "regular_both",
                    "skip_probability": random.uniform(0.05, 0.15)  # 5-15% chance to skip a day
                }
            # Weekend special (2L GOLD on weekends, 1L COW on weekdays) - 25% of dual subscribers
            elif pattern < 0.85:
                customer_patterns[customer.id] = {
                    "type": "weekend_special",
                    "skip_probability": random.uniform(0.05, 0.10)  # 5-10% chance to skip a day
                }
            # Alternating (GOLD one day, COW next day) - 15% of dual subscribers
            else:
                customer_patterns[customer.id] = {
                    "type": "alternating",
                    "skip_probability": random.uniform(0.10, 0.20)  # 10-20% chance to skip a day
                }

    # Create some holidays/special days when more people skip
    holidays = []
    # Add 2-3 random holidays
    for _ in range(random.randint(2, 3)):
        holiday = start_date + datetime.timedelta(days=random.randint(0, days_in_month - 1))
        holidays.append(holiday)
        
    print(f"Holidays/special days: {', '.join([h.strftime('%Y-%m-%d') for h in holidays])}")
    
    # Generate sales
    total_sales = 0
    sales_batch = []
    batch_size = 1000  # Process in batches of 1000 for better performance
    
    try:
        # Try to import tqdm for progress bar
        from tqdm import tqdm
        use_progress_bar = True
    except ImportError:
        use_progress_bar = False

    # Process each day in the month
    day_range = range(days_in_month)
    if use_progress_bar:
        from tqdm import tqdm
        day_iterator = tqdm(day_range, desc="Generating daily sales")
    else:
        day_iterator = day_range
        print("Generating daily sales...")
    
    for day_offset in day_iterator:
        current_date = start_date + datetime.timedelta(days=day_offset)
        is_weekend = current_date.weekday() >= 5  # Saturday or Sunday
        is_holiday = current_date in holidays
        
        for customer in customers:
            # Skip if customer isn't in our patterns (no milk types)
            if customer.id not in customer_patterns:
                continue
                
            pattern = customer_patterns[customer.id]
            skip_prob = pattern["skip_probability"]
            
            # Higher chance to skip on holidays and weekends
            if is_holiday:
                skip_prob *= 2.5  # Much higher chance to skip on holidays
            elif is_weekend:
                skip_prob *= 1.5  # Higher chance to skip on weekends
                
            # Skip this day for this customer?
            if random.random() < skip_prob:
                continue
                
            # Generate sales based on pattern
            pattern_type = pattern["type"]
            
            if pattern_type == "regular_cow":
                # 1L of COW milk daily
                sales_batch.append(Sale(
                    user=admin_user,
                    customer=customer,
                    milk_type=cow_milk,
                    date=current_date,
                    quantity=Decimal("1.0"),
                    rate=cow_milk.rate_per_liter
                ))
                
            elif pattern_type == "regular_gold":
                # 1L of GOLD milk daily
                sales_batch.append(Sale(
                    user=admin_user,
                    customer=customer,
                    milk_type=gold_milk,
                    date=current_date,
                    quantity=Decimal("1.0"),
                    rate=gold_milk.rate_per_liter
                ))
                
            elif pattern_type == "irregular_cow":
                # Irregular quantities of COW milk
                quantity = Decimal(str(random.choice([0.5, 1.0, 1.5])))
                sales_batch.append(Sale(
                    user=admin_user,
                    customer=customer,
                    milk_type=cow_milk,
                    date=current_date,
                    quantity=quantity,
                    rate=cow_milk.rate_per_liter
                ))
                
            elif pattern_type == "irregular_gold":
                # Irregular quantities of GOLD milk
                quantity = Decimal(str(random.choice([0.5, 1.0])))
                sales_batch.append(Sale(
                    user=admin_user,
                    customer=customer,
                    milk_type=gold_milk,
                    date=current_date,
                    quantity=quantity,
                    rate=gold_milk.rate_per_liter
                ))
                
            elif pattern_type == "regular_both":
                # 1L GOLD and 0.5L COW daily
                sales_batch.append(Sale(
                    user=admin_user,
                    customer=customer,
                    milk_type=gold_milk,
                    date=current_date,
                    quantity=Decimal("1.0"),
                    rate=gold_milk.rate_per_liter
                ))
                sales_batch.append(Sale(
                    user=admin_user,
                    customer=customer,
                    milk_type=cow_milk,
                    date=current_date,
                    quantity=Decimal("0.5"),
                    rate=cow_milk.rate_per_liter
                ))
                
            elif pattern_type == "weekend_special":
                # 2L GOLD on weekends, 1L COW on weekdays
                if is_weekend:
                    sales_batch.append(Sale(
                        user=admin_user,
                        customer=customer,
                        milk_type=gold_milk,
                        date=current_date,
                        quantity=Decimal("2.0"),
                        rate=gold_milk.rate_per_liter
                    ))
                else:
                    sales_batch.append(Sale(
                        user=admin_user,
                        customer=customer,
                        milk_type=cow_milk,
                        date=current_date,
                        quantity=Decimal("1.0"),
                        rate=cow_milk.rate_per_liter
                    ))
                    
            elif pattern_type == "alternating":
                # Alternate between GOLD and COW
                is_odd_day = day_offset % 2 == 1
                if is_odd_day:
                    sales_batch.append(Sale(
                        user=admin_user,
                        customer=customer,
                        milk_type=gold_milk,
                        date=current_date,
                        quantity=Decimal("1.0"),
                        rate=gold_milk.rate_per_liter
                    ))
                else:
                    sales_batch.append(Sale(
                        user=admin_user,
                        customer=customer,
                        milk_type=cow_milk,
                        date=current_date,
                        quantity=Decimal("1.0"),
                        rate=cow_milk.rate_per_liter
                    ))
            
            # Create sales in batches
            if len(sales_batch) >= batch_size:
                Sale.objects.bulk_create(sales_batch)
                total_sales += len(sales_batch)
                sales_batch = []
                if not use_progress_bar:
                    print(f"  Created {total_sales} sales so far...")
                
    # Create any remaining sales
    if sales_batch:
        Sale.objects.bulk_create(sales_batch)
        total_sales += len(sales_batch)
    
    # Generate some random payments for customers (about 70% of their total)
    print("\nGenerating payments for customers...")
    payments_created = 0
    payment_batch = []
    
    for customer in customers:
        # Calculate total sales amount
        total_sales_amount = Sale.objects.filter(customer=customer).aggregate(
            total=Sum(F('quantity') * F('rate'), output_field=DecimalField())
        )['total'] or Decimal('0')
        
        if total_sales_amount > 0:
            # Pay about 70% of the total (with some randomness)
            payment_percentage = Decimal(str(random.uniform(0.6, 0.8)))  # Pay between 60-80%, convert float to Decimal
            payment_amount = total_sales_amount * payment_percentage
            
            # Create a random payment date within the month
            payment_day = random.randint(10, days_in_month)  # Payment typically after some days
            payment_date = start_date + datetime.timedelta(days=payment_day)
            
            payment_batch.append(Payment(
                user=admin_user,
                customer=customer,
                date=payment_date,
                amount=payment_amount.quantize(Decimal('0.01')),  # Round to 2 decimal places
                description=f"Payment for {start_date.strftime('%B %Y')}"
            ))
            
            payments_created += 1
            
            # Create payments in batches
            if len(payment_batch) >= 50:
                Payment.objects.bulk_create(payment_batch)
                payment_batch = []
    
    # Create any remaining payments
    if payment_batch:
        Payment.objects.bulk_create(payment_batch)
    
    # Final report
    print(f"\nGenerated {total_sales} sales records for {start_date.strftime('%B %Y')}")
    print(f"Created {payments_created} payment records")
    print("Summary of customer patterns:")
    pattern_counts = {"regular_cow": 0, "regular_gold": 0, "irregular_cow": 0, 
                      "irregular_gold": 0, "regular_both": 0, "weekend_special": 0, 
                      "alternating": 0}
    
    for pattern in customer_patterns.values():
        pattern_counts[pattern["type"]] += 1
        
    for pattern_type, count in pattern_counts.items():
        print(f"  - {pattern_type}: {count} customers")
    
    print(f"\n{month_name} {year} data refresh complete!")

if __name__ == '__main__':
    # Set up command-line arguments
    parser = argparse.ArgumentParser(description='Generate test data for the dairy management app')
    parser.add_argument('--year', type=int, default=2025, help='Year to generate data for (default: 2025)')
    parser.add_argument('--month', type=int, default=3, help='Month to generate data for (default: 3 for March)')
    parser.add_argument('--customers', type=int, default=100, help='Number of customers to generate (default: 100)')
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducible results')
    
    args = parser.parse_args()
    
    # Run the data generation
    run(year=args.year, month=args.month, num_customers=args.customers, seed=args.seed)
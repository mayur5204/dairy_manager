#!/usr/bin/env python
import os
import sys
import random
import django
import datetime
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dairy_manager.settings')
django.setup()

# Import models after setting up Django
from django.contrib.auth.models import User
from dairy_app.models import Customer, MilkType, Sale
from django.utils import timezone
from django.db import transaction

def run():
    """Generate realistic milk sales for customers over a complete month."""
    print("Starting sales data generation...")

    # Get milk types
    try:
        cow_milk = MilkType.objects.get(name="COW")
        gold_milk = MilkType.objects.get(name="GOLD")
    except MilkType.DoesNotExist:
        print("ERROR: COW or GOLD milk types not found in the database.")
        print("Please run populate_customers.py first or create these milk types manually.")
        return

    # Get admin user
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("No admin user found. Please create a superuser first.")
        return

    # Get all customers
    customers = list(Customer.objects.all())
    if not customers:
        print("No customers found. Please run populate_customers.py first.")
        return
    
    print(f"Found {len(customers)} customers.")

    # Define month for data generation (current month)
    today = datetime.date.today()
    year = today.year
    month = today.month
    
    # Use previous month if we're early in the current month
    if today.day < 15:
        month = (today.month - 2) % 12 + 1  # Go back one month, handling year boundaries
        if month == 12:
            year = today.year - 1
            
    # Generate start and end dates for the month
    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
        
    days_in_month = (end_date - start_date).days + 1
    
    print(f"Generating sales for {start_date.strftime('%B %Y')} ({days_in_month} days)")

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
    
    # Delete existing sales for the month to avoid duplicates
    with transaction.atomic():
        deleted_count = Sale.objects.filter(
            date__gte=start_date, 
            date__lte=end_date
        ).delete()[0]
        
        if deleted_count > 0:
            print(f"Deleted {deleted_count} existing sales records for the selected month.")

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
    
    # Final report
    print(f"\nGenerated {total_sales} sales records for {start_date.strftime('%B %Y')}")
    print("Summary of customer patterns:")
    pattern_counts = {"regular_cow": 0, "regular_gold": 0, "irregular_cow": 0, 
                      "irregular_gold": 0, "regular_both": 0, "weekend_special": 0, 
                      "alternating": 0}
    
    for pattern in customer_patterns.values():
        pattern_counts[pattern["type"]] += 1
        
    for pattern_type, count in pattern_counts.items():
        print(f"  - {pattern_type}: {count} customers")
    
    print("\nSales generation complete!")

if __name__ == '__main__':
    run()
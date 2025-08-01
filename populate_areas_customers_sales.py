#!/usr/bin/env python
"""
Script to populate customers in two areas (Ganesh Colony and Prem Nagar) 
and generate sales data for the last two months.
Erases old data and creates fresh data.
"""
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
from dairy_app.models import Customer, MilkType, Sale, Payment, Area, MonthlyBalance
from django.utils import timezone
from django.db import transaction
from django.db import models

def clear_existing_data():
    """Clear all existing data to start fresh."""
    print("Clearing existing data...")
    
    # Delete in correct order due to foreign key constraints
    Sale.objects.all().delete()
    Payment.objects.all().delete()
    MonthlyBalance.objects.all().delete()
    Customer.objects.all().delete()
    Area.objects.all().delete()
    
    print("✅ All existing data cleared.")

def create_milk_types():
    """Create or get milk types."""
    print("Creating/getting milk types...")
    
    cow_milk, created = MilkType.objects.get_or_create(
        name="COW", 
        defaults={"rate_per_liter": Decimal("60.00")}
    )
    if created:
        print("✅ Created COW milk type (₹60/liter)")
    else:
        print("✅ COW milk type already exists")
    
    buffalo_milk, created = MilkType.objects.get_or_create(
        name="BUFFALO", 
        defaults={"rate_per_liter": Decimal("75.00")}
    )
    if created:
        print("✅ Created BUFFALO milk type (₹75/liter)")
    else:
        print("✅ BUFFALO milk type already exists")
    
    gold_milk, created = MilkType.objects.get_or_create(
        name="GOLD", 
        defaults={"rate_per_liter": Decimal("80.00")}
    )
    if created:
        print("✅ Created GOLD milk type (₹80/liter)")
    else:
        print("✅ GOLD milk type already exists")
    
    return cow_milk, buffalo_milk, gold_milk

def create_areas_and_customers():
    """Create two areas and populate them with customers."""
    print("Creating areas and customers...")
    
    # Get admin user
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("❌ No admin user found. Please create a superuser first.")
        return None, None, []
    
    # Create areas
    ganesh_colony, created = Area.objects.get_or_create(
        name="Ganesh Colony",
        user=admin_user,
        defaults={"description": "Ganesh Colony area for milk delivery"}
    )
    if created:
        print("✅ Created Ganesh Colony area")
    
    prem_nagar, created = Area.objects.get_or_create(
        name="Prem Nagar",
        user=admin_user,
        defaults={"description": "Prem Nagar area for milk delivery"}
    )
    if created:
        print("✅ Created Prem Nagar area")
    
    # Get milk types
    cow_milk = MilkType.objects.get(name="COW")
    buffalo_milk = MilkType.objects.get(name="BUFFALO")
    gold_milk = MilkType.objects.get(name="GOLD")
    
    # Customer names for Ganesh Colony
    ganesh_colony_customers = [
        "Rajesh Sharma", "Priya Patel", "Amit Kumar", "Sunita Devi", "Ramesh Gupta",
        "Geeta Agarwal", "Suresh Yadav", "Kavita Singh", "Manoj Verma", "Anita Jain",
        "Vinod Saxena", "Rekha Mishra", "Deepak Tiwari", "Meera Chauhan", "Ravi Shukla",
        "Neeta Pandey", "Gopal Das", "Seema Rastogi", "Harish Srivastava", "Pooja Bansal",
        "Ashok Goel", "Vandana Soni", "Mukesh Agarwal", "Sangeeta Roy", "Naresh Kumar",
        "Kumari Devi", "Santosh Gupta", "Usha Sharma", "Jagdish Prasad", "Mamta Singh"
    ]
    
    # Customer names for Prem Nagar  
    prem_nagar_customers = [
        "Vikram Malhotra", "Neha Kapoor", "Sanjay Arora", "Divya Joshi", "Rohit Bhatia",
        "Shweta Khanna", "Arun Sethi", "Priyanka Garg", "Nitin Aggarwal", "Rachna Chopra",
        "Manish Oberoi", "Swati Nanda", "Karan Mehra", "Richa Saini", "Varun Bhalla",
        "Sakshi Tandon", "Yash Bedi", "Simran Dhawan", "Rahul Sood", "Komal Bakshi",
        "Tarun Bajaj", "Preeti Gill", "Mohit Sachdeva", "Anjali Khurana", "Puneet Ahuja",
        "Ritu Bansal", "Vishal Lamba", "Nidhi Gupta", "Aman Sharma", "Kritika Jain"
    ]
    
    all_customers = []
    
    # Create customers for Ganesh Colony
    print("Creating customers for Ganesh Colony...")
    for i, name in enumerate(ganesh_colony_customers, 1):
        customer = Customer.objects.create(
            user=admin_user,
            name=name,
            address=f"House No. {i}, Ganesh Colony, Sector {random.randint(1, 15)}",
            phone=f"+91 {random.randint(7000000000, 9999999999)}",
            area=ganesh_colony
        )
        
        # Assign milk types randomly
        milk_type_choice = random.random()
        if milk_type_choice < 0.4:  # 40% only COW
            customer.milk_types.add(cow_milk)
        elif milk_type_choice < 0.7:  # 30% only BUFFALO
            customer.milk_types.add(buffalo_milk)
        elif milk_type_choice < 0.85:  # 15% only GOLD
            customer.milk_types.add(gold_milk)
        elif milk_type_choice < 0.95:  # 10% COW + BUFFALO
            customer.milk_types.add(cow_milk, buffalo_milk)
        else:  # 5% all three
            customer.milk_types.add(cow_milk, buffalo_milk, gold_milk)
        
        all_customers.append(customer)
    
    print(f"✅ Created {len(ganesh_colony_customers)} customers in Ganesh Colony")
    
    # Create customers for Prem Nagar
    print("Creating customers for Prem Nagar...")
    for i, name in enumerate(prem_nagar_customers, 1):
        customer = Customer.objects.create(
            user=admin_user,
            name=name,
            address=f"Plot No. {i}, Prem Nagar, Block {chr(65 + random.randint(0, 10))}",
            phone=f"+91 {random.randint(7000000000, 9999999999)}",
            area=prem_nagar
        )
        
        # Assign milk types randomly
        milk_type_choice = random.random()
        if milk_type_choice < 0.4:  # 40% only COW
            customer.milk_types.add(cow_milk)
        elif milk_type_choice < 0.7:  # 30% only BUFFALO
            customer.milk_types.add(buffalo_milk)
        elif milk_type_choice < 0.85:  # 15% only GOLD
            customer.milk_types.add(gold_milk)
        elif milk_type_choice < 0.95:  # 10% COW + BUFFALO
            customer.milk_types.add(cow_milk, buffalo_milk)
        else:  # 5% all three
            customer.milk_types.add(cow_milk, buffalo_milk, gold_milk)
        
        all_customers.append(customer)
    
    print(f"✅ Created {len(prem_nagar_customers)} customers in Prem Nagar")
    
    return ganesh_colony, prem_nagar, all_customers

def generate_sales_for_last_two_months(customers):
    """Generate realistic sales data for the last two months."""
    print("Generating sales data for last two months...")
    
    # Get current date and calculate last two months
    today = datetime.date.today()
    
    # Last month
    if today.month == 1:
        last_month = 12
        last_month_year = today.year - 1
    else:
        last_month = today.month - 1
        last_month_year = today.year
    
    # Month before last
    if last_month == 1:
        second_last_month = 12
        second_last_month_year = last_month_year - 1
    else:
        second_last_month = last_month - 1
        second_last_month_year = last_month_year
    
    print(f"Generating sales for {second_last_month}/{second_last_month_year} and {last_month}/{last_month_year}")
    
    # Get milk types
    milk_types = {
        'COW': MilkType.objects.get(name="COW"),
        'BUFFALO': MilkType.objects.get(name="BUFFALO"),
        'GOLD': MilkType.objects.get(name="GOLD")
    }
    
    total_sales_created = 0
    
    # Generate for both months
    for month_info in [
        {'month': second_last_month, 'year': second_last_month_year, 'name': 'second_last'},
        {'month': last_month, 'year': last_month_year, 'name': 'last'}
    ]:
        month = month_info['month']
        year = month_info['year']
        month_name = month_info['name']
        
        print(f"Generating sales for {month}/{year} ({month_name} month)...")
        
        # Get number of days in month
        if month in [1, 3, 5, 7, 8, 10, 12]:
            days_in_month = 31
        elif month in [4, 6, 9, 11]:
            days_in_month = 30
        else:  # February
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                days_in_month = 29
            else:
                days_in_month = 28
        
        month_sales = 0
        
        # Generate sales for each customer
        for customer in customers:
            customer_milk_types = list(customer.milk_types.all())
            
            if not customer_milk_types:
                continue
            
            # Each customer gets milk on 85-95% of days in the month
            active_days = random.randint(int(days_in_month * 0.85), int(days_in_month * 0.95))
            delivery_days = random.sample(range(1, days_in_month + 1), active_days)
            
            for day in delivery_days:
                sale_date = datetime.date(year, month, day)
                
                # For each milk type this customer uses
                for milk_type in customer_milk_types:
                    # 80% chance of getting this milk type on any given day
                    if random.random() < 0.8:
                        # Quantity based on milk type and some randomness
                        if milk_type.name == "COW":
                            base_quantity = random.uniform(0.5, 2.0)  # 0.5 to 2 liters
                        elif milk_type.name == "BUFFALO":
                            base_quantity = random.uniform(0.5, 1.5)  # 0.5 to 1.5 liters
                        else:  # GOLD
                            base_quantity = random.uniform(0.25, 1.0)  # 0.25 to 1 liter
                        
                        # Round to nearest 0.25
                        quantity = round(base_quantity * 4) / 4
                        
                        # Create sale
                        Sale.objects.create(
                            customer=customer,
                            milk_type=milk_type,
                            quantity=Decimal(str(quantity)),
                            rate=milk_type.rate_per_liter,
                            date=sale_date
                        )
                        
                        total_sales_created += 1
                        month_sales += 1
        
        print(f"✅ Created {month_sales} sales for {month}/{year}")
    
    print(f"✅ Total sales created: {total_sales_created}")

def generate_partial_payments(customers):
    """Generate some partial payments for customers."""
    print("Generating partial payments...")
    
    # Get last month for payment date
    today = datetime.date.today()
    if today.month == 1:
        last_month = 12
        last_month_year = today.year - 1
    else:
        last_month = today.month - 1
        last_month_year = today.year
    
    payments_created = 0
    
    # 60% of customers make some payment
    paying_customers = random.sample(customers, int(len(customers) * 0.6))
    
    for customer in paying_customers:
        # Calculate customer's total outstanding
        total_sales = Sale.objects.filter(customer=customer).aggregate(
            total=models.Sum(models.F('quantity') * models.F('rate'))
        )['total'] or Decimal('0')
        
        if total_sales > 0:
            # Pay between 30-80% of outstanding amount
            payment_percentage = random.uniform(0.3, 0.8)
            payment_amount = total_sales * Decimal(str(payment_percentage))
            payment_amount = payment_amount.quantize(Decimal('0.01'))
            
            # Random payment date in last month
            payment_day = random.randint(1, 28)  # Safe for all months
            payment_date = datetime.date(last_month_year, last_month, payment_day)
            
            Payment.objects.create(
                customer=customer,
                amount=payment_amount,
                date=payment_date,
                payment_for_month=last_month,
                payment_for_year=last_month_year
            )
            
            payments_created += 1
    
    print(f"✅ Created {payments_created} payments")

def print_summary():
    """Print summary of created data."""
    print("\n" + "="*60)
    print("DATA CREATION SUMMARY")
    print("="*60)
    
    # Areas
    areas = Area.objects.all()
    print(f"Areas created: {areas.count()}")
    for area in areas:
        customer_count = area.customers.count()
        print(f"  - {area.name}: {customer_count} customers")
    
    # Customers
    total_customers = Customer.objects.count()
    print(f"\nTotal customers: {total_customers}")
    
    # Sales
    total_sales = Sale.objects.count()
    sales_amount = Sale.objects.aggregate(
        total=models.Sum(models.F('quantity') * models.F('rate'))
    )['total'] or Decimal('0')
    print(f"Total sales records: {total_sales}")
    print(f"Total sales amount: ₹{sales_amount}")
    
    # Payments
    total_payments = Payment.objects.count()
    payment_amount = Payment.objects.aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0')
    print(f"Total payments: {total_payments}")
    print(f"Total payment amount: ₹{payment_amount}")
    
    # Outstanding
    outstanding = sales_amount - payment_amount
    print(f"Total outstanding: ₹{outstanding}")
    
    print("\n✅ Data population completed successfully!")

def run():
    """Main function to run the entire script."""
    print("🚀 Starting comprehensive data population...")
    print("This will erase all existing data and create fresh data.")
    
    try:
        with transaction.atomic():
            # Step 1: Clear existing data
            clear_existing_data()
            
            # Step 2: Create milk types
            cow_milk, buffalo_milk, gold_milk = create_milk_types()
            
            # Step 3: Create areas and customers
            ganesh_colony, prem_nagar, customers = create_areas_and_customers()
            
            if not customers:
                print("❌ Failed to create customers. Exiting.")
                return
            
            # Step 4: Generate sales for last two months
            generate_sales_for_last_two_months(customers)
            
            # Step 5: Generate partial payments
            generate_partial_payments(customers)
            
            # Step 6: Print summary
            print_summary()
            
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        raise

if __name__ == '__main__':
    run()

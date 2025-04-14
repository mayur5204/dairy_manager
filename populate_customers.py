#!/usr/bin/env python
import os
import sys
import random
import django
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dairy_manager.settings')
django.setup()

# Import models after setting up Django
from django.contrib.auth.models import User
from dairy_app.models import Customer, MilkType
from django.utils import timezone

def run():
    """Populate database with 500 customers with Indian names and phone numbers."""
    print("Starting to populate customer data...")

    # Ensure we have the milk types in the database
    cow_milk, created = MilkType.objects.get_or_create(
        name="COW", 
        defaults={"rate_per_liter": Decimal("60.00")}
    )
    gold_milk, created = MilkType.objects.get_or_create(
        name="GOLD", 
        defaults={"rate_per_liter": Decimal("80.00")}
    )

    # Get the first admin user as the owner for all records
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("No admin user found. Please create a superuser first.")
        return

    # List of common Indian first names
    first_names = [
        "Aakash", "Aarav", "Aditi", "Akshay", "Amit", "Ananya", "Anil", "Anjali", "Arjun", "Aruna",
        "Bharat", "Chetan", "Deepak", "Deepika", "Divya", "Ganesh", "Geeta", "Gopal", "Hari", "Harish",
        "Indira", "Ishaan", "Jaya", "Karan", "Kavita", "Kirti", "Krishna", "Kunal", "Lakshmi", "Madhav",
        "Manish", "Meera", "Mohan", "Nalini", "Naveen", "Neha", "Nitin", "Pooja", "Pradeep", "Pralabh",
        "Pranav", "Priya", "Rahul", "Rajesh", "Raju", "Ramesh", "Ravi", "Rekha", "Rohit", "Sachin",
        "Sanjay", "Sarita", "Shekhar", "Shikha", "Shivani", "Sunil", "Suresh", "Swati", "Tanvi", "Varun",
        "Vijay", "Vimal", "Vinay", "Vinod", "Vishal", "Yash", "Mayur", "Ajay", "Rakesh", "Neetu",
        "Vikram", "Saurabh", "Arun", "Jyoti", "Rajiv", "Sunita", "Preeti", "Manoj", "Anita", "Sudhir",
        "Vivek", "Nandini", "Aishwarya", "Raj", "Sonam", "Rishi", "Mohit", "Kavya", "Neeraj", "Shweta"
    ]

    # List of common Indian last names
    last_names = [
        "Acharya", "Agarwal", "Arora", "Banerjee", "Bhatt", "Chauhan", "Chopra", "Das", "Datta", "Desai", 
        "Deshpande", "Gandhi", "Gupta", "Iyer", "Jain", "Jha", "Kapur", "Khan", "Kumar", "Mahajan",
        "Mehra", "Menon", "Mishra", "Modi", "Mukherjee", "Nair", "Patel", "Patil", "Pillai", "Rao",
        "Reddy", "Saxena", "Sharma", "Singh", "Sinha", "Trivedi", "Varma", "Verma", "Yadav", "Bose",
        "Chatterjee", "Devi", "Dube", "Goel", "Gill", "Handal", "Johal", "Kaul", "Lal", "Malik",
        "Mistry", "Naidu", "Pandey", "Prasad", "Rajan", "Rana", "Sengupta", "Seth", "Talwar", "Tandon"
    ]

    # Creating 500 customers with random names and phone numbers
    customers_created = 0
    batch_size = 20  # Create in smaller batches for better progress reporting
    
    for batch in range(1, 501, batch_size):
        batch_customers = []
        
        for i in range(batch, min(batch + batch_size, 501)):
            # Generate random name
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            full_name = f"{first_name} {last_name}"
            
            # Generate random 10-digit phone number (Indian format)
            phone = f"+91 {random.randint(7000000000, 9999999999)}"
            
            # Create customer
            customer = Customer(
                user=admin_user,
                name=full_name,
                phone=phone,
                address=f"Sample Address, {random.randint(1, 500)}, {random.choice(['Delhi', 'Mumbai', 'Kolkata', 'Chennai', 'Bengaluru', 'Hyderabad', 'Pune', 'Ahmedabad', 'Jaipur', 'Surat'])}"
            )
            batch_customers.append(customer)
        
        # Bulk create customers for this batch
        Customer.objects.bulk_create(batch_customers)
        
        # Add milk types to each customer
        for customer in Customer.objects.filter(milk_types__isnull=True)[:batch_size]:
            # Random assignment of milk types: 40% COW, 30% GOLD, 30% both
            milk_type_choice = random.random()
            if milk_type_choice < 0.4:
                customer.milk_types.add(cow_milk)
            elif milk_type_choice < 0.7:
                customer.milk_types.add(gold_milk)
            else:
                customer.milk_types.add(cow_milk, gold_milk)
        
        customers_created += len(batch_customers)
        print(f"Created {customers_created} customers so far...")
    
    # Final count of customers in database
    customer_count = Customer.objects.count()
    print(f"Database now has {customer_count} customers.")
    print("Customer data population complete!")

if __name__ == '__main__':
    run()
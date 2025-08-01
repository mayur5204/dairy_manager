"""
Django management command to populate areas, customers, and sales data.
Usage: python manage.py populate_demo_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from dairy_app.models import Customer, MilkType, Sale, Payment, Area, MonthlyBalance
from django.db import transaction, models
from decimal import Decimal
import random
import datetime


class Command(BaseCommand):
    help = 'Populate demo data: areas (Ganesh Colony, Prem Nagar), customers, and sales for last 2 months'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating new data',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting demo data population...')
        )

        try:
            with transaction.atomic():
                if options['clear']:
                    self.clear_existing_data()
                
                # Get admin user first
                admin_user = User.objects.filter(is_superuser=True).first()
                if not admin_user:
                    self.stdout.write(self.style.ERROR('❌ No admin user found. Please create a superuser first.'))
                    return
                
                self.create_milk_types()
                areas, customers = self.create_areas_and_customers()
                
                if customers:
                    self.generate_sales_for_last_two_months(customers, admin_user)
                    self.generate_partial_payments(customers, admin_user)
                    self.print_summary()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error occurred: {str(e)}')
            )
            raise

    def clear_existing_data(self):
        """Clear all existing data."""
        self.stdout.write('Clearing existing data...')
        
        Sale.objects.all().delete()
        Payment.objects.all().delete()
        MonthlyBalance.objects.all().delete()
        Customer.objects.all().delete()
        Area.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS('✅ All existing data cleared.'))

    def create_milk_types(self):
        """Create or get milk types."""
        self.stdout.write('Creating/getting milk types...')
        
        cow_milk, created = MilkType.objects.get_or_create(
            name="COW", 
            defaults={"rate_per_liter": Decimal("60.00")}
        )
        if created:
            self.stdout.write('✅ Created COW milk type (₹60/liter)')
        
        buffalo_milk, created = MilkType.objects.get_or_create(
            name="BUFFALO", 
            defaults={"rate_per_liter": Decimal("75.00")}
        )
        if created:
            self.stdout.write('✅ Created BUFFALO milk type (₹75/liter)')
        
        gold_milk, created = MilkType.objects.get_or_create(
            name="GOLD", 
            defaults={"rate_per_liter": Decimal("80.00")}
        )
        if created:
            self.stdout.write('✅ Created GOLD milk type (₹80/liter)')

    def create_areas_and_customers(self):
        """Create two areas and populate them with customers."""
        self.stdout.write('Creating areas and customers...')
        
        # Get admin user
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR('❌ No admin user found. Please create a superuser first.'))
            return [], []
        
        # Create areas
        ganesh_colony, created = Area.objects.get_or_create(
            name="Ganesh Colony",
            user=admin_user,
            defaults={"description": "Ganesh Colony area for milk delivery"}
        )
        if created:
            self.stdout.write('✅ Created Ganesh Colony area')
        
        prem_nagar, created = Area.objects.get_or_create(
            name="Prem Nagar",
            user=admin_user,
            defaults={"description": "Prem Nagar area for milk delivery"}
        )
        if created:
            self.stdout.write('✅ Created Prem Nagar area')
        
        # Get milk types
        cow_milk = MilkType.objects.get(name="COW")
        buffalo_milk = MilkType.objects.get(name="BUFFALO")
        gold_milk = MilkType.objects.get(name="GOLD")
        
        # Customer data
        ganesh_colony_customers = [
            "Rajesh Sharma", "Priya Patel", "Amit Kumar", "Sunita Devi", "Ramesh Gupta",
            "Geeta Agarwal", "Suresh Yadav", "Kavita Singh", "Manoj Verma", "Anita Jain",
            "Vinod Saxena", "Rekha Mishra", "Deepak Tiwari", "Meera Chauhan", "Ravi Shukla",
            "Neeta Pandey", "Gopal Das", "Seema Rastogi", "Harish Srivastava", "Pooja Bansal",
            "Ashok Goel", "Vandana Soni", "Mukesh Agarwal", "Sangeeta Roy", "Naresh Kumar",
            "Kumari Devi", "Santosh Gupta", "Usha Sharma", "Jagdish Prasad", "Mamta Singh"
        ]
        
        prem_nagar_customers = [
            "Vikram Malhotra", "Neha Kapoor", "Sanjay Arora", "Divya Joshi", "Rohit Bhatia",
            "Shweta Khanna", "Arun Sethi", "Priyanka Garg", "Nitin Aggarwal", "Rachna Chopra",
            "Manish Oberoi", "Swati Nanda", "Karan Mehra", "Richa Saini", "Varun Bhalla",
            "Sakshi Tandon", "Yash Bedi", "Simran Dhawan", "Rahul Sood", "Komal Bakshi",
            "Tarun Bajaj", "Preeti Gill", "Mohit Sachdeva", "Anjali Khurana", "Puneet Ahuja",
            "Ritu Bansal", "Vishal Lamba", "Nidhi Gupta", "Aman Sharma", "Kritika Jain"
        ]
        
        all_customers = []
        
        # Create customers for both areas
        for area, customer_names in [(ganesh_colony, ganesh_colony_customers), (prem_nagar, prem_nagar_customers)]:
            for i, name in enumerate(customer_names, 1):
                if area == ganesh_colony:
                    address = f"House No. {i}, Ganesh Colony, Sector {random.randint(1, 15)}"
                else:
                    address = f"Plot No. {i}, Prem Nagar, Block {chr(65 + random.randint(0, 10))}"
                
                customer = Customer.objects.create(
                    user=admin_user,
                    name=name,
                    address=address,
                    phone=f"+91 {random.randint(7000000000, 9999999999)}",
                    area=area
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
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {len(all_customers)} customers total'))
        return [ganesh_colony, prem_nagar], all_customers

    def generate_sales_for_last_two_months(self, customers, admin_user):
        """Generate sales data for the last two months."""
        self.stdout.write('Generating sales data for last two months...')
        
        today = datetime.date.today()
        
        # Calculate last two months
        if today.month == 1:
            last_month = 12
            last_month_year = today.year - 1
        else:
            last_month = today.month - 1
            last_month_year = today.year
        
        if last_month == 1:
            second_last_month = 12
            second_last_month_year = last_month_year - 1
        else:
            second_last_month = last_month - 1
            second_last_month_year = last_month_year
        
        self.stdout.write(f'Generating for {second_last_month}/{second_last_month_year} and {last_month}/{last_month_year}')
        
        total_sales = 0
        
        # Generate for both months
        for month, year in [(second_last_month, second_last_month_year), (last_month, last_month_year)]:
            # Get days in month
            if month in [1, 3, 5, 7, 8, 10, 12]:
                days_in_month = 31
            elif month in [4, 6, 9, 11]:
                days_in_month = 30
            else:  # February
                if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                    days_in_month = 29
                else:
                    days_in_month = 28
            
            # Generate sales for each customer
            for customer in customers:
                customer_milk_types = list(customer.milk_types.all())
                
                if not customer_milk_types:
                    continue
                
                # Active days (85-95% of month)
                active_days = random.randint(int(days_in_month * 0.85), int(days_in_month * 0.95))
                delivery_days = random.sample(range(1, days_in_month + 1), active_days)
                
                for day in delivery_days:
                    sale_date = datetime.date(year, month, day)
                    
                    for milk_type in customer_milk_types:
                        # 80% chance of getting this milk type
                        if random.random() < 0.8:
                            # Quantity based on milk type
                            if milk_type.name == "COW":
                                base_quantity = random.uniform(0.5, 2.0)
                            elif milk_type.name == "BUFFALO":
                                base_quantity = random.uniform(0.5, 1.5)
                            else:  # GOLD
                                base_quantity = random.uniform(0.25, 1.0)
                            
                            # Round to nearest 0.25
                            quantity = round(base_quantity * 4) / 4
                            
                            Sale.objects.create(
                                user=admin_user,
                                customer=customer,
                                milk_type=milk_type,
                                quantity=Decimal(str(quantity)),
                                rate=milk_type.rate_per_liter,
                                date=sale_date
                            )
                            
                            total_sales += 1
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {total_sales} sales records'))

    def generate_partial_payments(self, customers, admin_user):
        """Generate some partial payments."""
        self.stdout.write('Generating partial payments...')
        
        today = datetime.date.today()
        if today.month == 1:
            last_month = 12
            last_month_year = today.year - 1
        else:
            last_month = today.month - 1
            last_month_year = today.year
        
        payments_created = 0
        
        # 60% of customers make payments
        paying_customers = random.sample(customers, int(len(customers) * 0.6))
        
        for customer in paying_customers:
            # Calculate total outstanding
            total_sales = Sale.objects.filter(customer=customer).aggregate(
                total=models.Sum(models.F('quantity') * models.F('rate'))
            )['total'] or Decimal('0')
            
            if total_sales > 0:
                # Pay 30-80% of outstanding
                payment_percentage = random.uniform(0.3, 0.8)
                payment_amount = total_sales * Decimal(str(payment_percentage))
                payment_amount = payment_amount.quantize(Decimal('0.01'))
                
                # Random payment date in last month
                payment_day = random.randint(1, 28)
                payment_date = datetime.date(last_month_year, last_month, payment_day)
                
                Payment.objects.create(
                    user=admin_user,
                    customer=customer,
                    amount=payment_amount,
                    date=payment_date,
                    payment_for_month=last_month,
                    payment_for_year=last_month_year
                )
                
                payments_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {payments_created} payments'))

    def print_summary(self):
        """Print summary of created data."""
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('DATA CREATION SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        # Areas
        areas = Area.objects.all()
        self.stdout.write(f'Areas: {areas.count()}')
        for area in areas:
            customer_count = area.customers.count()
            self.stdout.write(f'  - {area.name}: {customer_count} customers')
        
        # Sales & Payments
        total_sales = Sale.objects.count()
        sales_amount = Sale.objects.aggregate(
            total=models.Sum(models.F('quantity') * models.F('rate'))
        )['total'] or Decimal('0')
        
        total_payments = Payment.objects.count()
        payment_amount = Payment.objects.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        outstanding = sales_amount - payment_amount
        
        self.stdout.write(f'\nSales records: {total_sales} (₹{sales_amount})')
        self.stdout.write(f'Payments: {total_payments} (₹{payment_amount})')
        self.stdout.write(f'Outstanding: ₹{outstanding}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Demo data population completed!'))

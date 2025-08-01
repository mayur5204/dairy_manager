# Demo Data Population Guide

This guide explains how to populate your dairy management system with demo data including:
- 2 Areas: Ganesh Colony and Prem Nagar
- 60 Customers (30 in each area)
- Sales data for the last 2 months
- Partial payment records

## Method 1: Using Django Management Command (Recommended)

### Basic Usage:
```bash
python manage.py populate_demo_data
```

### Clear existing data and create fresh data:
```bash
python manage.py populate_demo_data --clear
```

### Full Example:
```bash
# Navigate to your project directory
cd /path/to/dairy_manager

# Activate virtual environment (if using one)
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Run the command
python manage.py populate_demo_data --clear
```

## Method 2: Direct Script Execution

### Run the standalone script:
```bash
python populate_areas_customers_sales.py
```

## What Gets Created:

### 🏢 Areas (2):
- **Ganesh Colony** - 30 customers
- **Prem Nagar** - 30 customers

### 🥛 Milk Types (3):
- **COW** - ₹60 per liter
- **BUFFALO** - ₹75 per liter  
- **GOLD** - ₹80 per liter

### 👥 Customers (60 total):

**Ganesh Colony (30 customers):**
- Rajesh Sharma, Priya Patel, Amit Kumar, Sunita Devi, Ramesh Gupta
- Geeta Agarwal, Suresh Yadav, Kavita Singh, Manoj Verma, Anita Jain
- Vinod Saxena, Rekha Mishra, Deepak Tiwari, Meera Chauhan, Ravi Shukla
- Neeta Pandey, Gopal Das, Seema Rastogi, Harish Srivastava, Pooja Bansal
- Ashok Goel, Vandana Soni, Mukesh Agarwal, Sangeeta Roy, Naresh Kumar
- Kumari Devi, Santosh Gupta, Usha Sharma, Jagdish Prasad, Mamta Singh

**Prem Nagar (30 customers):**
- Vikram Malhotra, Neha Kapoor, Sanjay Arora, Divya Joshi, Rohit Bhatia
- Shweta Khanna, Arun Sethi, Priyanka Garg, Nitin Aggarwal, Rachna Chopra
- Manish Oberoi, Swati Nanda, Karan Mehra, Richa Saini, Varun Bhalla
- Sakshi Tandon, Yash Bedi, Simran Dhawan, Rahul Sood, Komal Bakshi
- Tarun Bajaj, Preeti Gill, Mohit Sachdeva, Anjali Khurana, Puneet Ahuja
- Ritu Bansal, Vishal Lamba, Nidhi Gupta, Aman Sharma, Kritika Jain

### 🛒 Customer Milk Type Distribution:
- **40%** - Only COW milk
- **30%** - Only BUFFALO milk
- **15%** - Only GOLD milk
- **10%** - COW + BUFFALO milk
- **5%** - All three types

### 📊 Sales Data:
- **Time Period**: Last 2 complete months
- **Frequency**: 85-95% of days per month per customer
- **Quantities**: 
  - COW: 0.5-2.0 liters per delivery
  - BUFFALO: 0.5-1.5 liters per delivery
  - GOLD: 0.25-1.0 liters per delivery
- **Daily Probability**: 80% chance of getting each milk type per day

### 💰 Payment Data:
- **Coverage**: 60% of customers make payments
- **Amount**: 30-80% of their total outstanding amount
- **Timing**: Random dates in the last month

## Expected Results:

After running the script, you should see:
- **~3,000-4,000 sales records** for 2 months
- **~36 payment records** (60% of 60 customers)
- **Realistic outstanding balances** for most customers
- **Area-wise customer distribution**

## Sample Output:
```
🚀 Starting demo data population...
Clearing existing data...
✅ All existing data cleared.
Creating/getting milk types...
✅ Created COW milk type (₹60/liter)
✅ Created BUFFALO milk type (₹75/liter)
✅ Created GOLD milk type (₹80/liter)
Creating areas and customers...
✅ Created Ganesh Colony area
✅ Created Prem Nagar area
✅ Created 60 customers total
Generating sales data for last two months...
Generating for 6/2025 and 7/2025
✅ Created 3847 sales records
Generating partial payments...
✅ Created 36 payments

============================================================
DATA CREATION SUMMARY
============================================================
Areas: 2
  - Ganesh Colony: 30 customers
  - Prem Nagar: 30 customers

Sales records: 3847 (₹245,678.50)
Payments: 36 (₹134,521.25)
Outstanding: ₹111,157.25

✅ Demo data population completed!
```

## Verification:

After running the script, you can verify the data by:

1. **Check the dashboard** - Visit `/dairy/` to see the summary
2. **Browse customers** - Visit `/dairy/customers/` to see all customers
3. **View sales** - Visit `/dairy/sales/` to see recent sales
4. **Check reports** - Visit `/dairy/reports/` to see financial summaries

## Customization:

To modify the script for your needs:

1. **Change customer names** - Edit the `ganesh_colony_customers` and `prem_nagar_customers` lists
2. **Adjust milk prices** - Modify the `rate_per_liter` values in `create_milk_types()`
3. **Change time period** - Modify the month calculation logic in `generate_sales_for_last_two_months()`
4. **Adjust quantities** - Change the `random.uniform()` ranges for different milk types
5. **Payment percentages** - Modify the payment logic in `generate_partial_payments()`

## Troubleshooting:

### Error: "No admin user found"
**Solution:** Create a superuser first:
```bash
python manage.py createsuperuser
```

### Error: "MilkType matching query does not exist"
**Solution:** The script creates milk types automatically, but if you get this error, run:
```bash
python manage.py shell
>>> from dairy_app.models import MilkType
>>> from decimal import Decimal
>>> MilkType.objects.create(name="COW", rate_per_liter=Decimal("60.00"))
>>> MilkType.objects.create(name="BUFFALO", rate_per_liter=Decimal("75.00"))
>>> MilkType.objects.create(name="GOLD", rate_per_liter=Decimal("80.00"))
```

### Error: Database issues
**Solution:** Run migrations first:
```bash
python manage.py makemigrations
python manage.py migrate
```

## Notes:

- 🔄 **Idempotent**: Safe to run multiple times
- 🗑️ **--clear flag**: Completely wipes existing data
- 📱 **Realistic data**: Phone numbers, addresses, and quantities are realistic
- 💾 **Transaction safety**: All operations are wrapped in database transactions
- 🎯 **Performance**: Optimized for bulk operations

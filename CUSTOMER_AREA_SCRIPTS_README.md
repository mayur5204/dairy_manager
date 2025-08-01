# Customer-Area Assignment Scripts

This directory contains scripts to manage customer-area assignments in the Dairy Management System.

## Scripts Overview

### 1. `assign_customers_to_areas.py`
Basic script to assign existing customers to available areas.

**Usage:**
```bash
python assign_customers_to_areas.py [options]
```

**Options:**
- `--strategy={even|random|alphabetical|round_robin}` - Assignment strategy (default: even)
- `--user-id=<id>` - Filter by specific user ID
- `--dry-run` - Show what would be assigned without making changes
- `--force` - Reassign customers even if they already have an area

**Examples:**
```bash
# Assign unassigned customers evenly across areas
python assign_customers_to_areas.py

# Random assignment with dry run
python assign_customers_to_areas.py --strategy=random --dry-run

# Alphabetical assignment for specific user
python assign_customers_to_areas.py --user-id=1 --strategy=alphabetical
```

### 2. `create_areas.py`
Script to create sample areas for customer assignment.

**Usage:**
```bash
python create_areas.py --user-id=<id> [options]
```

**Options:**
- `--user-id=<id>` - User ID to create areas for (required)
- `--dry-run` - Show what would be created without making changes
- `--custom` - Allow input of custom areas instead of predefined ones

**Examples:**
```bash
# Create sample areas for user ID 1
python create_areas.py --user-id=1

# Preview what would be created
python create_areas.py --user-id=1 --dry-run

# Create custom areas interactively
python create_areas.py --user-id=1 --custom
```

### 3. `manage_customer_areas.py`
Comprehensive management script with multiple commands.

**Usage:**
```bash
python manage_customer_areas.py <command> [options]
```

**Commands:**

#### `status` - Show current status
```bash
python manage_customer_areas.py status [--user-id=<id>]
```

#### `create` - Create sample areas
```bash
python manage_customer_areas.py create --user-id=<id> [--dry-run]
```

#### `assign` - Assign customers to areas
```bash
python manage_customer_areas.py assign [options]
```
Options: `--user-id`, `--strategy`, `--force`, `--dry-run`

#### `report` - Generate detailed report
```bash
python manage_customer_areas.py report [--user-id=<id>]
```

#### `balance` - Balance customer distribution
```bash
python manage_customer_areas.py balance [--user-id=<id>] [--dry-run]
```

## Assignment Strategies

1. **even** - Distribute customers evenly across all areas (default)
2. **random** - Randomly assign customers to areas
3. **alphabetical** - Sort customers alphabetically, then distribute evenly
4. **round_robin** - Assign customers in round-robin fashion
5. **balance** - Balance based on existing customer count in each area

## Workflow Examples

### First Time Setup
```bash
# 1. Check current status
python manage_customer_areas.py status --user-id=1

# 2. Create areas if none exist
python manage_customer_areas.py create --user-id=1

# 3. Assign customers to areas
python manage_customer_areas.py assign --user-id=1 --strategy=even

# 4. Generate a report
python manage_customer_areas.py report --user-id=1
```

### Rebalancing Existing Assignments
```bash
# Check current distribution
python manage_customer_areas.py status --user-id=1

# Preview rebalancing
python manage_customer_areas.py balance --user-id=1 --dry-run

# Execute rebalancing
python manage_customer_areas.py balance --user-id=1
```

### Adding New Customers
```bash
# After adding new customers, assign only unassigned ones
python manage_customer_areas.py assign --user-id=1 --strategy=balance

# Or force reassignment of all customers
python manage_customer_areas.py assign --user-id=1 --strategy=even --force
```

## Prerequisites

1. Django environment must be properly set up
2. Database migrations must be run
3. At least one user account must exist
4. Customers should exist in the database (use `populate_customers.py` if needed)

## Getting User ID

To find user IDs, you can use Django shell:
```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
users = User.objects.all()
for user in users:
    print(f"ID: {user.id}, Username: {user.username}")
```

## Sample Areas Created

The scripts create these predefined areas:
- North Zone - Northern delivery area
- South Zone - Southern delivery area  
- East Zone - Eastern delivery area
- West Zone - Western delivery area
- Central Zone - Central delivery area

## Notes

- Always use `--dry-run` first to preview changes
- The `--force` option will reassign ALL customers, even those already assigned
- Each area belongs to a specific user (multi-tenant support)
- Customer counts are balanced as evenly as possible across areas
- All scripts support filtering by user ID for multi-user environments

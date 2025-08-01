#!/usr/bin/env python
"""
Script to assign existing customers to available areas in the dairy management system.

This script will:
1. Retrieve all existing customers that are not assigned to any area
2. Retrieve all available areas in the database
3. Distribute customers evenly across areas
4. Optionally allow for specific assignment strategies (alphabetical, random, etc.)

Usage:
    python assign_customers_to_areas.py [--strategy=<strategy>] [--user-id=<user_id>] [--dry-run]
    
Strategies:
    - even: Distribute customers evenly across all areas (default)
    - random: Randomly assign customers to areas
    - alphabetical: Assign customers alphabetically to areas
    - round_robin: Assign customers in round-robin fashion
"""

import os
import sys
import django
import argparse
import random
from collections import defaultdict

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dairy_manager.settings')
django.setup()

# Import models after setting up Django
from django.contrib.auth.models import User
from dairy_app.models import Customer, Area


def get_unassigned_customers(user=None):
    """Get all customers that are not assigned to any area."""
    queryset = Customer.objects.filter(area__isnull=True)
    if user:
        queryset = queryset.filter(user=user)
    return queryset.order_by('name')


def get_available_areas(user=None):
    """Get all available areas in the database."""
    queryset = Area.objects.all()
    if user:
        queryset = queryset.filter(user=user)
    return queryset.order_by('name')


def assign_customers_evenly(customers, areas):
    """Assign customers evenly across all areas."""
    if not areas:
        print("No areas available for assignment.")
        return {}
    
    assignments = defaultdict(list)
    area_cycle = iter(areas)
    current_area = next(area_cycle, None)
    
    for customer in customers:
        if current_area is None:
            # Reset cycle if we've gone through all areas
            area_cycle = iter(areas)
            current_area = next(area_cycle, None)
        
        assignments[current_area].append(customer)
        try:
            current_area = next(area_cycle)
        except StopIteration:
            current_area = None
    
    return assignments


def assign_customers_randomly(customers, areas):
    """Randomly assign customers to areas."""
    if not areas:
        print("No areas available for assignment.")
        return {}
    
    assignments = defaultdict(list)
    
    for customer in customers:
        random_area = random.choice(areas)
        assignments[random_area].append(customer)
    
    return assignments


def assign_customers_alphabetically(customers, areas):
    """Assign customers alphabetically to areas."""
    if not areas:
        print("No areas available for assignment.")
        return {}
    
    assignments = defaultdict(list)
    customers_per_area = len(customers) // len(areas) if areas else 0
    remainder = len(customers) % len(areas) if areas else 0
    
    customer_index = 0
    
    for i, area in enumerate(areas):
        # Calculate how many customers this area should get
        customers_for_this_area = customers_per_area
        if i < remainder:
            customers_for_this_area += 1
        
        # Assign customers to this area
        for _ in range(customers_for_this_area):
            if customer_index < len(customers):
                assignments[area].append(customers[customer_index])
                customer_index += 1
    
    return assignments


def assign_customers_round_robin(customers, areas):
    """Assign customers in round-robin fashion to areas."""
    if not areas:
        print("No areas available for assignment.")
        return {}
    
    assignments = defaultdict(list)
    
    for i, customer in enumerate(customers):
        area = areas[i % len(areas)]
        assignments[area].append(customer)
    
    return assignments


def display_assignment_summary(assignments):
    """Display a summary of the assignment."""
    print("\n" + "="*60)
    print("ASSIGNMENT SUMMARY")
    print("="*60)
    
    total_customers = sum(len(customers) for customers in assignments.values())
    
    for area, customers in assignments.items():
        print(f"\nArea: {area.name}")
        print(f"  Description: {area.description or 'No description'}")
        print(f"  Customers to assign: {len(customers)}")
        print(f"  Current customer count: {area.get_customer_count()}")
        print(f"  Total after assignment: {area.get_customer_count() + len(customers)}")
        
        if len(customers) <= 10:
            print("  Customer names:")
            for customer in customers:
                print(f"    - {customer.name}")
        else:
            print("  Sample customer names:")
            for customer in customers[:5]:
                print(f"    - {customer.name}")
            print(f"    ... and {len(customers) - 5} more")
    
    print(f"\nTotal customers to be assigned: {total_customers}")
    print("="*60)


def execute_assignment(assignments, dry_run=False):
    """Execute the customer assignment to areas."""
    if dry_run:
        print("\n[DRY RUN] No actual changes will be made to the database.")
        return
    
    print("\nExecuting customer assignments...")
    
    total_assigned = 0
    
    for area, customers in assignments.items():
        for customer in customers:
            customer.area = area
            customer.save()
            total_assigned += 1
        
        print(f"Assigned {len(customers)} customers to area '{area.name}'")
    
    print(f"\nSuccessfully assigned {total_assigned} customers to areas!")


def main():
    """Main function to run the customer assignment script."""
    parser = argparse.ArgumentParser(
        description="Assign existing customers to available areas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Strategies:
  even        - Distribute customers evenly across all areas (default)
  random      - Randomly assign customers to areas
  alphabetical- Assign customers alphabetically to areas
  round_robin - Assign customers in round-robin fashion

Examples:
  python assign_customers_to_areas.py
  python assign_customers_to_areas.py --strategy=random --dry-run
  python assign_customers_to_areas.py --user-id=1 --strategy=alphabetical
        """
    )
    
    parser.add_argument(
        '--strategy',
        choices=['even', 'random', 'alphabetical', 'round_robin'],
        default='even',
        help='Assignment strategy to use (default: even)'
    )
    
    parser.add_argument(
        '--user-id',
        type=int,
        help='Specific user ID to filter customers and areas (optional)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be assigned without making actual changes'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Reassign customers even if they already have an area assigned'
    )
    
    args = parser.parse_args()
    
    print("Dairy Management System - Customer Area Assignment")
    print("="*55)
    
    # Get user if specified
    user = None
    if args.user_id:
        try:
            user = User.objects.get(id=args.user_id)
            print(f"Filtering for user: {user.username} (ID: {user.id})")
        except User.DoesNotExist:
            print(f"Error: User with ID {args.user_id} does not exist.")
            return
    
    # Get unassigned customers
    if args.force:
        customers = Customer.objects.all()
        if user:
            customers = customers.filter(user=user)
        customers = customers.order_by('name')
        print(f"Found {customers.count()} total customers (including those already assigned)")
    else:
        customers = get_unassigned_customers(user)
        print(f"Found {customers.count()} unassigned customers")
    
    if not customers:
        print("No customers found that need area assignment.")
        return
    
    # Get available areas
    areas = get_available_areas(user)
    print(f"Found {areas.count()} available areas")
    
    if not areas:
        print("No areas available for assignment.")
        print("Please create at least one area before running this script.")
        return
    
    print(f"\nUsing assignment strategy: {args.strategy}")
    
    # Convert querysets to lists for processing
    customer_list = list(customers)
    area_list = list(areas)
    
    # Apply assignment strategy
    if args.strategy == 'even':
        assignments = assign_customers_evenly(customer_list, area_list)
    elif args.strategy == 'random':
        assignments = assign_customers_randomly(customer_list, area_list)
    elif args.strategy == 'alphabetical':
        assignments = assign_customers_alphabetically(customer_list, area_list)
    elif args.strategy == 'round_robin':
        assignments = assign_customers_round_robin(customer_list, area_list)
    
    if not assignments:
        print("No assignments could be made.")
        return
    
    # Display assignment summary
    display_assignment_summary(assignments)
    
    # Ask for confirmation if not in dry-run mode
    if not args.dry_run:
        while True:
            confirm = input("\nDo you want to proceed with these assignments? (y/n): ").lower().strip()
            if confirm in ['y', 'yes']:
                break
            elif confirm in ['n', 'no']:
                print("Assignment cancelled.")
                return
            else:
                print("Please enter 'y' for yes or 'n' for no.")
    
    # Execute the assignment
    execute_assignment(assignments, dry_run=args.dry_run)


if __name__ == '__main__':
    main()

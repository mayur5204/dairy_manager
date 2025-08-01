#!/usr/bin/env python
"""
Comprehensive Customer-Area Management Script for Dairy Management System

This script provides a complete solution for managing customer-area assignments:
1. View current status of customers and areas
2. Create areas if needed
3. Assign customers to areas using various strategies
4. Generate reports and statistics

Usage:
    python manage_customer_areas.py <command> [options]

Commands:
    status      - Show current status of customers and areas
    create      - Create new areas
    assign      - Assign customers to areas
    report      - Generate detailed reports
    balance     - Balance customer distribution across areas
    help        - Show detailed help for each command
"""

import os
import sys
import django
import argparse
import random
from collections import defaultdict, Counter

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dairy_manager.settings')
django.setup()

# Import models after setting up Django
from django.contrib.auth.models import User
from dairy_app.models import Customer, Area


class CustomerAreaManager:
    """Main class for managing customer-area assignments."""
    
    def __init__(self, user_id=None):
        """Initialize the manager with optional user filtering."""
        self.user = None
        if user_id:
            try:
                self.user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise ValueError(f"User with ID {user_id} does not exist.")
    
    def get_customers(self, unassigned_only=False):
        """Get customers filtered by user and assignment status."""
        queryset = Customer.objects.all()
        if self.user:
            queryset = queryset.filter(user=self.user)
        if unassigned_only:
            queryset = queryset.filter(area__isnull=True)
        return queryset.order_by('name')
    
    def get_areas(self):
        """Get areas filtered by user."""
        queryset = Area.objects.all()
        if self.user:
            queryset = queryset.filter(user=self.user)
        return queryset.order_by('name')
    
    def show_status(self):
        """Display current status of customers and areas."""
        print("CUSTOMER-AREA STATUS REPORT")
        print("="*50)
        
        customers = self.get_customers()
        areas = self.get_areas()
        unassigned_customers = self.get_customers(unassigned_only=True)
        
        print(f"Total customers: {customers.count()}")
        print(f"Total areas: {areas.count()}")
        print(f"Unassigned customers: {unassigned_customers.count()}")
        print(f"Assigned customers: {customers.count() - unassigned_customers.count()}")
        
        if areas.exists():
            print(f"\nArea Distribution:")
            area_stats = []
            for area in areas:
                customer_count = area.get_customer_count()
                area_stats.append((area, customer_count))
            
            # Sort by customer count (descending)
            area_stats.sort(key=lambda x: x[1], reverse=True)
            
            for area, count in area_stats:
                percentage = (count / customers.count() * 100) if customers.count() > 0 else 0
                print(f"  {area.name}: {count} customers ({percentage:.1f}%)")
        
        if unassigned_customers.exists():
            print(f"\nSample unassigned customers:")
            sample_size = min(10, unassigned_customers.count())
            for customer in unassigned_customers[:sample_size]:
                print(f"  - {customer.name}")
            if unassigned_customers.count() > sample_size:
                print(f"  ... and {unassigned_customers.count() - sample_size} more")
    
    def create_sample_areas(self, dry_run=False):
        """Create sample areas for testing and demonstration."""
        sample_areas = [
            {'name': 'North Zone', 'description': 'Northern delivery area'},
            {'name': 'South Zone', 'description': 'Southern delivery area'},
            {'name': 'East Zone', 'description': 'Eastern delivery area'},
            {'name': 'West Zone', 'description': 'Western delivery area'},
            {'name': 'Central Zone', 'description': 'Central delivery area'},
        ]
        
        if not self.user:
            print("Error: User must be specified to create areas.")
            return False
        
        created_count = 0
        skipped_count = 0
        
        for area_data in sample_areas:
            existing = Area.objects.filter(
                user=self.user,
                name=area_data['name']
            ).first()
            
            if existing:
                skipped_count += 1
                continue
            
            if not dry_run:
                Area.objects.create(
                    user=self.user,
                    name=area_data['name'],
                    description=area_data['description']
                )
            created_count += 1
        
        print(f"Areas created: {created_count}")
        print(f"Areas skipped (already exist): {skipped_count}")
        return created_count > 0
    
    def assign_customers(self, strategy='even', force=False, dry_run=False):
        """Assign customers to areas using the specified strategy."""
        if force:
            customers = list(self.get_customers())
        else:
            customers = list(self.get_customers(unassigned_only=True))
        
        areas = list(self.get_areas())
        
        if not customers:
            print("No customers found for assignment.")
            return False
        
        if not areas:
            print("No areas available for assignment.")
            return False
        
        # Apply assignment strategy
        assignments = self._apply_strategy(customers, areas, strategy)
        
        if not assignments:
            print("No assignments could be made.")
            return False
        
        # Display summary
        self._display_assignment_summary(assignments)
        
        if not dry_run:
            return self._execute_assignments(assignments)
        return True
    
    def _apply_strategy(self, customers, areas, strategy):
        """Apply the specified assignment strategy."""
        assignments = defaultdict(list)
        
        if strategy == 'even':
            # Distribute evenly
            for i, customer in enumerate(customers):
                area = areas[i % len(areas)]
                assignments[area].append(customer)
        
        elif strategy == 'random':
            # Random assignment
            for customer in customers:
                area = random.choice(areas)
                assignments[area].append(customer)
        
        elif strategy == 'alphabetical':
            # Sort customers alphabetically, then distribute evenly
            customers.sort(key=lambda c: c.name)
            customers_per_area = len(customers) // len(areas)
            remainder = len(customers) % len(areas)
            
            customer_index = 0
            for i, area in enumerate(areas):
                count = customers_per_area + (1 if i < remainder else 0)
                for _ in range(count):
                    if customer_index < len(customers):
                        assignments[area].append(customers[customer_index])
                        customer_index += 1
        
        elif strategy == 'balance':
            # Balance based on existing customer count
            # Get current counts for each area
            area_counts = [(area, area.get_customer_count()) for area in areas]
            
            for customer in customers:
                # Find area with minimum customers
                min_area = min(area_counts, key=lambda x: x[1])
                assignments[min_area[0]].append(customer)
                # Update count for next iteration
                for i, (area, count) in enumerate(area_counts):
                    if area == min_area[0]:
                        area_counts[i] = (area, count + 1)
                        break
        
        return assignments
    
    def _display_assignment_summary(self, assignments):
        """Display assignment summary."""
        print("\nASSIGNMENT SUMMARY")
        print("-" * 40)
        
        total_customers = sum(len(customers) for customers in assignments.values())
        
        for area, customers in assignments.items():
            current_count = area.get_customer_count()
            new_total = current_count + len(customers)
            
            print(f"\n{area.name}:")
            print(f"  Current customers: {current_count}")
            print(f"  New assignments: {len(customers)}")
            print(f"  Total after assignment: {new_total}")
            
            if len(customers) <= 5:
                for customer in customers:
                    print(f"    + {customer.name}")
            else:
                for customer in customers[:3]:
                    print(f"    + {customer.name}")
                print(f"    + ... and {len(customers) - 3} more")
        
        print(f"\nTotal assignments: {total_customers}")
    
    def _execute_assignments(self, assignments):
        """Execute the customer assignments."""
        total_assigned = 0
        
        for area, customers in assignments.items():
            for customer in customers:
                customer.area = area
                customer.save()
                total_assigned += 1
        
        print(f"\nSuccessfully assigned {total_assigned} customers!")
        return True
    
    def generate_report(self):
        """Generate a detailed report of customer-area distribution."""
        print("DETAILED CUSTOMER-AREA REPORT")
        print("="*60)
        
        customers = self.get_customers()
        areas = self.get_areas()
        
        print(f"Report generated for: {self.user.username if self.user else 'All users'}")
        print(f"Total customers: {customers.count()}")
        print(f"Total areas: {areas.count()}")
        
        # Area details
        print(f"\nAREA DETAILS:")
        print("-" * 40)
        
        if not areas.exists():
            print("No areas found.")
            return
        
        area_data = []
        for area in areas:
            area_customers = area.customers.all()
            area_data.append({
                'area': area,
                'customer_count': area_customers.count(),
                'customers': list(area_customers[:10])  # Limit for display
            })
        
        # Sort by customer count
        area_data.sort(key=lambda x: x['customer_count'], reverse=True)
        
        for data in area_data:
            area = data['area']
            count = data['customer_count']
            customers_sample = data['customers']
            
            print(f"\n{area.name} (ID: {area.id})")
            print(f"  Description: {area.description or 'No description'}")
            print(f"  Customer count: {count}")
            
            if customers_sample:
                print(f"  Sample customers:")
                for customer in customers_sample:
                    print(f"    - {customer.name}")
                if count > len(customers_sample):
                    print(f"    ... and {count - len(customers_sample)} more")
        
        # Unassigned customers
        unassigned = self.get_customers(unassigned_only=True)
        if unassigned.exists():
            print(f"\nUNASSIGNED CUSTOMERS ({unassigned.count()}):")
            print("-" * 40)
            sample_size = min(20, unassigned.count())
            for customer in unassigned[:sample_size]:
                print(f"  - {customer.name}")
            if unassigned.count() > sample_size:
                print(f"  ... and {unassigned.count() - sample_size} more")
    
    def balance_areas(self, dry_run=False):
        """Balance customer distribution across areas."""
        customers = list(self.get_customers())
        areas = list(self.get_areas())
        
        if not customers or not areas:
            print("Insufficient data for balancing.")
            return False
        
        target_per_area = len(customers) // len(areas)
        remainder = len(customers) % len(areas)
        
        print(f"Balancing {len(customers)} customers across {len(areas)} areas")
        print(f"Target per area: {target_per_area} (with {remainder} areas getting +1)")
        
        # Clear all current assignments
        moves = []
        
        customer_index = 0
        for i, area in enumerate(areas):
            target_count = target_per_area + (1 if i < remainder else 0)
            
            for j in range(target_count):
                if customer_index < len(customers):
                    customer = customers[customer_index]
                    if customer.area != area:
                        moves.append((customer, customer.area, area))
                    customer_index += 1
        
        if not moves:
            print("All customers are already balanced.")
            return True
        
        print(f"\nPlanned moves: {len(moves)}")
        for customer, old_area, new_area in moves[:10]:
            old_name = old_area.name if old_area else "Unassigned"
            print(f"  {customer.name}: {old_name} → {new_area.name}")
        
        if len(moves) > 10:
            print(f"  ... and {len(moves) - 10} more moves")
        
        if not dry_run:
            for customer, old_area, new_area in moves:
                customer.area = new_area
                customer.save()
            print(f"\nCompleted {len(moves)} customer moves!")
        
        return True


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Customer-Area Management",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show current status')
    status_parser.add_argument('--user-id', type=int, help='Filter by user ID')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create sample areas')
    create_parser.add_argument('--user-id', type=int, required=True, help='User ID (required)')
    create_parser.add_argument('--dry-run', action='store_true', help='Show what would be created')
    
    # Assign command
    assign_parser = subparsers.add_parser('assign', help='Assign customers to areas')
    assign_parser.add_argument('--user-id', type=int, help='Filter by user ID')
    assign_parser.add_argument('--strategy', choices=['even', 'random', 'alphabetical', 'balance'], 
                              default='even', help='Assignment strategy')
    assign_parser.add_argument('--force', action='store_true', help='Reassign all customers')
    assign_parser.add_argument('--dry-run', action='store_true', help='Show what would be assigned')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate detailed report')
    report_parser.add_argument('--user-id', type=int, help='Filter by user ID')
    
    # Balance command
    balance_parser = subparsers.add_parser('balance', help='Balance customer distribution')
    balance_parser.add_argument('--user-id', type=int, help='Filter by user ID')
    balance_parser.add_argument('--dry-run', action='store_true', help='Show what would be moved')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # Initialize manager
        manager = CustomerAreaManager(args.user_id)
        
        # Execute command
        if args.command == 'status':
            manager.show_status()
        
        elif args.command == 'create':
            if manager.create_sample_areas(dry_run=args.dry_run):
                print("Sample areas creation completed.")
            else:
                print("No areas were created.")
        
        elif args.command == 'assign':
            if manager.assign_customers(
                strategy=args.strategy,
                force=args.force,
                dry_run=args.dry_run
            ):
                print("Customer assignment completed.")
            else:
                print("No assignments were made.")
        
        elif args.command == 'report':
            manager.generate_report()
        
        elif args.command == 'balance':
            if manager.balance_areas(dry_run=args.dry_run):
                print("Balance operation completed.")
            else:
                print("Balance operation failed.")
    
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == '__main__':
    main()

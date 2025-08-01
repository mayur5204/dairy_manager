#!/usr/bin/env python
"""
Script to create sample areas for the dairy management system.

This script will create predefined areas that can be used for customer assignment.
Areas represent delivery zones or geographical regions for milk delivery.

Usage:
    python create_areas.py [--user-id=<user_id>] [--dry-run]
"""

import os
import sys
import django
import argparse

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dairy_manager.settings')
django.setup()

# Import models after setting up Django
from django.contrib.auth.models import User
from dairy_app.models import Area


def get_sample_areas():
    """Return a list of sample areas with names and descriptions."""
    return [
        {
            'name': 'North Zone',
            'description': 'Northern delivery area covering residential complexes and markets'
        },
        {
            'name': 'South Zone',
            'description': 'Southern delivery area including commercial and residential areas'
        },
        {
            'name': 'East Zone',
            'description': 'Eastern delivery area covering industrial and residential sectors'
        },
        {
            'name': 'West Zone',
            'description': 'Western delivery area including suburban and urban neighborhoods'
        },
        {
            'name': 'Central Zone',
            'description': 'Central delivery area covering city center and main markets'
        },
        {
            'name': 'Downtown',
            'description': 'Downtown business district and high-rise residential areas'
        },
        {
            'name': 'Suburbs',
            'description': 'Suburban residential areas and housing societies'
        },
        {
            'name': 'Industrial Area',
            'description': 'Industrial zone and nearby worker residential areas'
        },
        {
            'name': 'Old City',
            'description': 'Traditional old city area with narrow lanes and markets'
        },
        {
            'name': 'New Development',
            'description': 'Newly developed residential and commercial complexes'
        }
    ]


def create_areas(user, area_data, dry_run=False):
    """Create areas for the specified user."""
    created_areas = []
    skipped_areas = []
    
    for area_info in area_data:
        # Check if area already exists for this user
        existing_area = Area.objects.filter(
            user=user,
            name=area_info['name']
        ).first()
        
        if existing_area:
            skipped_areas.append(area_info['name'])
            continue
        
        if not dry_run:
            area = Area.objects.create(
                user=user,
                name=area_info['name'],
                description=area_info['description']
            )
            created_areas.append(area)
        else:
            created_areas.append(area_info['name'])
    
    return created_areas, skipped_areas


def main():
    """Main function to create sample areas."""
    parser = argparse.ArgumentParser(
        description="Create sample areas for customer assignment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script creates predefined areas that represent delivery zones
for the dairy management system. Areas can be used to organize
customers by geographical location for efficient delivery routing.

Examples:
  python create_areas.py --user-id=1
  python create_areas.py --user-id=1 --dry-run
        """
    )
    
    parser.add_argument(
        '--user-id',
        type=int,
        required=True,
        help='User ID to create areas for (required)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be created without making actual changes'
    )
    
    parser.add_argument(
        '--custom',
        action='store_true',
        help='Allow input of custom areas instead of using predefined ones'
    )
    
    args = parser.parse_args()
    
    print("Dairy Management System - Area Creation")
    print("="*42)
    
    # Get user
    try:
        user = User.objects.get(id=args.user_id)
        print(f"Creating areas for user: {user.username} (ID: {user.id})")
    except User.DoesNotExist:
        print(f"Error: User with ID {args.user_id} does not exist.")
        return
    
    # Check existing areas
    existing_areas = Area.objects.filter(user=user)
    print(f"User currently has {existing_areas.count()} areas")
    
    if existing_areas.count() > 0:
        print("\nExisting areas:")
        for area in existing_areas:
            customer_count = area.get_customer_count()
            print(f"  - {area.name}: {customer_count} customers")
    
    if args.custom:
        # Custom area creation
        print("\nCustom area creation mode")
        area_data = []
        
        while True:
            print(f"\nEnter details for area #{len(area_data) + 1} (or press Enter to finish):")
            name = input("Area name: ").strip()
            
            if not name:
                break
            
            description = input("Area description (optional): ").strip()
            
            area_data.append({
                'name': name,
                'description': description or f"Custom delivery area: {name}"
            })
            
            print(f"Added area: {name}")
        
        if not area_data:
            print("No custom areas were entered.")
            return
    else:
        # Use predefined areas
        area_data = get_sample_areas()
        print(f"\nUsing {len(area_data)} predefined sample areas")
    
    print(f"\nAreas to be created:")
    for i, area_info in enumerate(area_data, 1):
        print(f"  {i}. {area_info['name']}")
        print(f"     Description: {area_info['description']}")
    
    if args.dry_run:
        print("\n[DRY RUN] No actual changes will be made to the database.")
    else:
        # Ask for confirmation
        while True:
            confirm = input("\nDo you want to create these areas? (y/n): ").lower().strip()
            if confirm in ['y', 'yes']:
                break
            elif confirm in ['n', 'no']:
                print("Area creation cancelled.")
                return
            else:
                print("Please enter 'y' for yes or 'n' for no.")
    
    # Create the areas
    created_areas, skipped_areas = create_areas(user, area_data, dry_run=args.dry_run)
    
    print("\n" + "="*50)
    print("AREA CREATION SUMMARY")
    print("="*50)
    
    if created_areas:
        print(f"\nSuccessfully created {len(created_areas)} areas:")
        for area in created_areas:
            if args.dry_run:
                print(f"  ✓ {area}")
            else:
                print(f"  ✓ {area.name} (ID: {area.id})")
    
    if skipped_areas:
        print(f"\nSkipped {len(skipped_areas)} areas (already exist):")
        for area_name in skipped_areas:
            print(f"  - {area_name}")
    
    if not args.dry_run and created_areas:
        print(f"\nTotal areas for user '{user.username}': {Area.objects.filter(user=user).count()}")
        print("\nYou can now run 'assign_customers_to_areas.py' to assign customers to these areas.")


if __name__ == '__main__':
    main()

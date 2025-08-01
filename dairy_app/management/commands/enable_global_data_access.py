"""
Django management command to make areas visible to all superusers without duplicating data.
This command modifies the application behavior to share data across superusers.
Usage: python manage.py enable_global_data_access
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from dairy_app.models import Customer, Area
from django.db import transaction


class Command(BaseCommand):
    help = 'Enable global data access for all superusers by updating area and customer ownership'

    def add_arguments(self, parser):
        parser.add_argument(
            '--transfer-to-user',
            type=str,
            help='Transfer all data to this superuser (default: first superuser)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually making changes',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting global data access configuration...')
        )

        try:
            with transaction.atomic():
                # Get all superusers
                superusers = User.objects.filter(is_superuser=True)
                
                if not superusers.exists():
                    self.stdout.write(self.style.ERROR('❌ No superusers found.'))
                    return

                # Get target user (the one who will "own" all data)
                if options['transfer_to_user']:
                    try:
                        target_user = User.objects.get(username=options['transfer_to_user'], is_superuser=True)
                    except User.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'❌ Target user "{options["transfer_to_user"]}" not found or not a superuser.'))
                        return
                else:
                    target_user = superusers.first()
                
                self.stdout.write(f'🎯 Target user: "{target_user.username}"')
                
                # Get all areas from all users
                all_areas = Area.objects.all()
                all_customers = Customer.objects.all()
                
                self.stdout.write(f'📊 Found {all_areas.count()} areas and {all_customers.count()} customers across all users')

                if options['dry_run']:
                    self.stdout.write('\n[DRY RUN] Changes that would be made:')
                    
                    # Show areas that would be transferred
                    areas_to_transfer = all_areas.exclude(user=target_user)
                    if areas_to_transfer.exists():
                        self.stdout.write(f'📍 Would transfer {areas_to_transfer.count()} areas to {target_user.username}:')
                        for area in areas_to_transfer:
                            self.stdout.write(f'  • {area.name} (from {area.user.username})')
                    
                    # Show customers that would be transferred
                    customers_to_transfer = all_customers.exclude(user=target_user)
                    if customers_to_transfer.exists():
                        self.stdout.write(f'👥 Would transfer {customers_to_transfer.count()} customers to {target_user.username}:')
                        for customer in customers_to_transfer[:10]:  # Show first 10
                            self.stdout.write(f'  • {customer.name} (from {customer.user.username})')
                        if customers_to_transfer.count() > 10:
                            self.stdout.write(f'  ... and {customers_to_transfer.count() - 10} more')
                    
                    self.stdout.write(self.style.WARNING('🔍 DRY RUN completed - no changes were made'))
                    self.stdout.write(
                        self.style.SUCCESS(
                            '💡 After running without --dry-run, all superusers will be able to access all areas and customers.'
                        )
                    )
                else:
                    # Transfer all areas to target user
                    areas_updated = all_areas.exclude(user=target_user).update(user=target_user)
                    
                    # Transfer all customers to target user
                    customers_updated = all_customers.exclude(user=target_user).update(user=target_user)
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Successfully transferred {areas_updated} areas and {customers_updated} customers to {target_user.username}'
                        )
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            '🌐 All areas and customers are now accessible to all superusers!\n'
                            '   Note: Sales and payments remain linked to their original creators.'
                        )
                    )
                
                # Show final summary
                self.print_summary()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error occurred: {str(e)}')
            )
            raise

    def print_summary(self):
        """Print a summary of current data distribution."""
        self.stdout.write('\n📊 Current Data Distribution:')
        self.stdout.write('=' * 50)
        
        superusers = User.objects.filter(is_superuser=True)
        for user in superusers:
            areas = Area.objects.filter(user=user)
            customers = Customer.objects.filter(user=user)
            
            self.stdout.write(f'\n👤 User: {user.username}')
            self.stdout.write(f'   📍 Areas: {areas.count()}')
            self.stdout.write(f'   👥 Customers: {customers.count()}')
            
            if areas.exists():
                for area in areas:
                    customer_count = Customer.objects.filter(area=area).count()
                    self.stdout.write(f'     • {area.name}: {customer_count} customers')
        
        self.stdout.write('\n💡 Tips:')
        self.stdout.write('- All superusers can now access all areas and customers')
        self.stdout.write('- Use the area filter in customer list to organize data')
        self.stdout.write('- Sales and payment records maintain their original user associations')

"""
Django management command to share areas, customers, and other data with all superusers.
This command creates duplicate entries for all superusers so they can access the same data.
Usage: python manage.py share_data_with_superusers
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from dairy_app.models import Customer, MilkType, Sale, Payment, Area, MonthlyBalance
from django.db import transaction
from decimal import Decimal
import datetime


class Command(BaseCommand):
    help = 'Share existing areas and customers with all superusers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source-user',
            type=str,
            help='Username of the source user whose data should be shared (default: first superuser)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually making changes',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting data sharing process...')
        )

        try:
            with transaction.atomic():
                # Get all superusers
                superusers = User.objects.filter(is_superuser=True)
                
                if not superusers.exists():
                    self.stdout.write(self.style.ERROR('❌ No superusers found.'))
                    return

                # Get source user
                if options['source_user']:
                    try:
                        source_user = User.objects.get(username=options['source_user'], is_superuser=True)
                    except User.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'❌ Source user "{options["source_user"]}" not found or not a superuser.'))
                        return
                else:
                    source_user = superusers.first()
                
                self.stdout.write(f'📤 Using "{source_user.username}" as source user')
                
                # Get source user's areas
                source_areas = Area.objects.filter(user=source_user)
                
                if not source_areas.exists():
                    self.stdout.write(self.style.WARNING(f'⚠️  Source user "{source_user.username}" has no areas to share.'))
                    return

                self.stdout.write(f'📊 Found {source_areas.count()} areas to share')

                # Share areas with all other superusers
                for target_user in superusers:
                    if target_user == source_user:
                        continue  # Skip source user
                    
                    self.stdout.write(f'👤 Processing user: {target_user.username}')
                    
                    areas_created = 0
                    customers_created = 0
                    
                    for source_area in source_areas:
                        # Check if target user already has an area with the same name
                        existing_area = Area.objects.filter(
                            user=target_user, 
                            name=source_area.name
                        ).first()
                        
                        if existing_area:
                            self.stdout.write(f'  📍 Area "{source_area.name}" already exists for {target_user.username}')
                            target_area = existing_area
                        else:
                            if options['dry_run']:
                                self.stdout.write(f'  [DRY RUN] Would create area: {source_area.name}')
                                continue
                            else:
                                # Create new area for target user
                                target_area = Area.objects.create(
                                    user=target_user,
                                    name=source_area.name,
                                    description=source_area.description
                                )
                                areas_created += 1
                                self.stdout.write(f'  ✅ Created area: {source_area.name}')
                        
                        # Get customers in this source area
                        source_customers = Customer.objects.filter(area=source_area)
                        
                        for source_customer in source_customers:
                            # Check if target user already has a customer with the same name in this area
                            existing_customer = Customer.objects.filter(
                                user=target_user,
                                area=target_area,
                                name=source_customer.name
                            ).first()
                            
                            if existing_customer:
                                self.stdout.write(f'    👤 Customer "{source_customer.name}" already exists')
                                continue
                            
                            if options['dry_run']:
                                self.stdout.write(f'    [DRY RUN] Would create customer: {source_customer.name}')
                                continue
                            
                            # Create new customer for target user
                            target_customer = Customer.objects.create(
                                user=target_user,
                                name=source_customer.name,
                                address=source_customer.address,
                                phone=source_customer.phone,
                                area=target_area,
                                date_joined=source_customer.date_joined
                            )
                            
                            # Copy milk types
                            target_customer.milk_types.set(source_customer.milk_types.all())
                            
                            customers_created += 1
                            self.stdout.write(f'    ✅ Created customer: {source_customer.name}')
                    
                    if not options['dry_run']:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  📈 Summary for {target_user.username}: '
                                f'{areas_created} areas, {customers_created} customers created'
                            )
                        )

                if options['dry_run']:
                    self.stdout.write(self.style.WARNING('🔍 DRY RUN completed - no changes were made'))
                else:
                    self.stdout.write(self.style.SUCCESS('✅ Data sharing completed successfully!'))
                    self.stdout.write(
                        self.style.SUCCESS(
                            '💡 All superusers now have access to the same areas and customers. '
                            'Sales and payment data remain linked to the original user.'
                        )
                    )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error occurred: {str(e)}')
            )
            raise

    def print_summary(self):
        """Print a summary of what was shared."""
        self.stdout.write('\n📊 Data Sharing Summary:')
        self.stdout.write('=' * 50)
        
        superusers = User.objects.filter(is_superuser=True)
        for user in superusers:
            areas = Area.objects.filter(user=user)
            customers = Customer.objects.filter(user=user)
            
            self.stdout.write(f'\n👤 User: {user.username}')
            self.stdout.write(f'   📍 Areas: {areas.count()}')
            self.stdout.write(f'   👥 Customers: {customers.count()}')
            
            for area in areas:
                customer_count = Customer.objects.filter(area=area).count()
                self.stdout.write(f'     • {area.name}: {customer_count} customers')

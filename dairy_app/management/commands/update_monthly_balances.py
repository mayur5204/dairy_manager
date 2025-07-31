from django.core.management.base import BaseCommand
from dairy_app.models import Customer, MonthlyBalance
from django.utils import timezone

class Command(BaseCommand):
    help = 'Calculates and updates monthly balances for all customers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--customer',
            type=int,
            help='Update balances only for a specific customer ID',
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Update balances only for a specific year',
        )
        parser.add_argument(
            '--month',
            type=int,
            help='Update balances only for a specific month (requires --year)',
        )

    def handle(self, *args, **options):
        customer_id = options.get('customer')
        year = options.get('year')
        month = options.get('month')
        
        # Validate month if provided
        if month and not (1 <= month <= 12):
            self.stdout.write(self.style.ERROR('Month must be between 1 and 12'))
            return
        
        # If month is provided but year is not, use current year
        if month and not year:
            year = timezone.now().year
            self.stdout.write(self.style.WARNING(f'Year not provided, using current year: {year}'))
            
        # Get customers to process
        if customer_id:
            try:
                customers = [Customer.objects.get(pk=customer_id)]
                self.stdout.write(f'Processing customer ID: {customer_id}')
            except Customer.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Customer with ID {customer_id} not found'))
                return
        else:
            customers = Customer.objects.all()
            self.stdout.write(f'Processing all customers ({customers.count()} total)')
        
        # Process each customer
        updated_count = 0
        for customer in customers:
            if year and month:
                # Update specific month for this customer
                result = MonthlyBalance.update_monthly_balances(customer, year, month)
                if result:
                    updated_count += 1
                    self.stdout.write(f'Updated balance for {customer.name}: {month}/{year}')
            else:
                # Update all months for this customer
                results = MonthlyBalance.update_monthly_balances(customer)
                if results:
                    updated_count += 1
                    self.stdout.write(f'Updated {len(results)} monthly balances for {customer.name}')
            
        self.stdout.write(self.style.SUCCESS(
            f'Successfully updated monthly balances for {updated_count} customers'
        ))

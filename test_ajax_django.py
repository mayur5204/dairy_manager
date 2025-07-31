#!/usr/bin/env python3
"""
Test script to check if the AJAX functionality works correctly using Django test client
"""
import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dairy_manager.settings')
django.setup()

from django.test import Client, override_settings
from django.contrib.auth.models import User
from dairy_app.models import Customer, MonthlyBalance

@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
def test_ajax_request():
    # Get a customer with unpaid months
    customer = Customer.objects.first()
    if not customer:
        print("No customers found!")
        return
    
    print(f"Testing with customer: {customer.name} (ID: {customer.id})")
    
    # Update monthly balances
    MonthlyBalance.update_monthly_balances(customer)
    
    # Check if there are unpaid months
    unpaid_balances = MonthlyBalance.objects.filter(
        customer=customer,
        is_paid=False,
        sales_amount__gt=0
    )
    print(f"Found {unpaid_balances.count()} unpaid months for this customer")
    
    # Create test client and login
    client = Client()
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("No admin user found!")
        return
    
    # Login the user
    client.force_login(user)
    print(f"Logged in as: {user.username}")
    
    # Test the regular page load first
    url = f"/en/dairy/payments/add/"
    response = client.get(url, {'customer': customer.id})
    print(f"Regular page request status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Error loading page: {response.content}")
        return
    
    print("Regular page loaded successfully!")
    
    # Now test the AJAX request
    headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
    ajax_response = client.get(url, {
        'customer': customer.id,
        'fetch_unpaid': 'true',
        'timestamp': '123456789'
    }, **headers)
    
    print(f"AJAX response status: {ajax_response.status_code}")
    print(f"AJAX response content length: {len(ajax_response.content)}")
    print(f"Response content:\n{ajax_response.content.decode('utf-8')}")

if __name__ == "__main__":
    test_ajax_request()

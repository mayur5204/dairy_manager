#!/usr/bin/env python3
"""
Test script to check if the AJAX functionality works correctly
"""
import os
import sys
import django
import requests

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dairy_manager.settings')
django.setup()

from dairy_app.models import Customer, MonthlyBalance
from django.contrib.auth.models import User

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
    
    # Create a test user session
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("No admin user found!")
        return
    
    # Make the AJAX request similar to what the JavaScript does
    url = f"http://127.0.0.1:8000/en/dairy/payments/add/"
    
    session = requests.Session()
    
    # First get the page to get CSRF token
    print(f"Requesting page: {url}?customer={customer.id}")
    response = session.get(url, params={'customer': customer.id})
    print(f"Initial request status: {response.status_code}")
    
    if response.status_code == 302:
        print("Redirected to login - authentication required")
        return
    
    # Extract CSRF token (simplified - in a real test we'd parse it properly)
    csrf_token = None
    for line in response.text.split('\n'):
        if 'csrf_token' in line and 'value=' in line:
            csrf_token = line.split('value="')[1].split('"')[0]
            break
    
    if not csrf_token:
        print("Could not find CSRF token")
        return
    
    print(f"Found CSRF token: {csrf_token[:10]}...")
    
    # Now make the AJAX request
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrf_token,
    }
    
    params = {
        'customer': customer.id,
        'fetch_unpaid': 'true',
        'timestamp': '123456789'
    }
    
    print(f"Making AJAX request...")
    ajax_response = session.get(url, params=params, headers=headers)
    print(f"AJAX response status: {ajax_response.status_code}")
    print(f"AJAX response content length: {len(ajax_response.text)}")
    print(f"First 200 chars of response:\n{ajax_response.text[:200]}")

if __name__ == "__main__":
    test_ajax_request()

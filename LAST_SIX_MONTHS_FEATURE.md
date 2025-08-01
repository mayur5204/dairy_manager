# Last 6 Months Balance Status Feature

## Overview
This feature enhances the customer information page to display the monthly balance status for the last 6 months in a user-friendly format.

## Changes Made

### 1. Customer Model Enhancement (`dairy_app/models.py`)
Added a new method `get_last_six_months_status()` to the Customer model that:
- Calculates balance status for the last 6 months
- Returns structured data with month names, sales, payments, balances, and status
- Provides color-coded status information (paid, pending, no_sales)
- Uses existing MonthlyBalance model for data consistency

### 2. View Updates (`dairy_app/views.py`)
Modified `CustomerDetailView` to:
- Changed monthly balance display from 12 months to 6 months
- Added `last_six_months_status` context variable using the new model method
- Maintains backward compatibility with existing monthly_balances context

### 3. Template Enhancements (`dairy_app/templates/dairy_app/customer_detail.html`)
Enhanced the customer detail page with:
- **Visual Month Overview**: Badge-style display showing each month's status at a glance
- **Detailed Table**: Comprehensive table with sales, payments, balance, and status
- **Color-coded Status**: Green for paid, red for pending, gray for no sales
- **Improved User Experience**: Hover effects and intuitive visual design
- **Responsive Design**: Works well on both desktop and mobile devices

### 4. CSS Styling (`templates/base.html`)
Added new CSS classes for:
- `.six-months-status`: Container styling for the 6-months display
- `.month-card`: Individual month display cards with hover effects
- `.text-pending`, `.text-paid`, `.text-no-sales`: Status-specific text colors
- Responsive badge layouts and interactive elements

### 5. Testing Script (`test_last_six_months.py`)
Created a test script to:
- Verify the new functionality works correctly
- Test with specific customers or multiple customers
- Display formatted output for verification
- Help with debugging and validation

## Usage

### For Users
1. Navigate to any customer's detail page
2. View the "Last 6 Months Balance Status" section
3. See at-a-glance status in the badge overview
4. Review detailed information in the table below

### For Developers
```python
# Get last 6 months status for a customer
customer = Customer.objects.get(id=1)
status = customer.get_last_six_months_status()

# Each item in status contains:
# - year, month, month_name, month_short
# - sales_amount, payment_amount, balance
# - status, status_class, status_text, is_paid
```

### Testing
```bash
# Test the functionality
python test_last_six_months.py

# Test specific customer
python test_last_six_months.py --customer-id=1
```

## Status Types

1. **Paid** (Green badge)
   - Month has sales and is fully paid
   - Balance is zero or negative (advance payment)

2. **Pending** (Red badge)
   - Month has sales but outstanding balance
   - Balance is positive (amount due)

3. **No Sales** (Gray badge)
   - No sales recorded for the month
   - Balance is zero

## Benefits

1. **Quick Visual Assessment**: Users can instantly see payment status across 6 months
2. **Improved Cash Flow Management**: Easy identification of pending payments
3. **Better Customer Relationships**: Quick access to payment history during conversations
4. **Mobile-Friendly**: Responsive design works on all devices
5. **Backward Compatible**: Existing functionality remains intact

## File Structure
```
dairy_app/
├── models.py                 # Added get_last_six_months_status() method
├── views.py                  # Updated CustomerDetailView
└── templates/dairy_app/
    └── customer_detail.html  # Enhanced UI for 6-months display

templates/
└── base.html                 # Added CSS styling

test_last_six_months.py       # Testing script
```

## Future Enhancements

Potential improvements that could be added:
- Export 6-months status to PDF/Excel
- Email reminders for pending months
- Filtering and sorting options
- Summary statistics dashboard
- Bulk payment processing for multiple months

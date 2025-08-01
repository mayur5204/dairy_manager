# Multi-Month Payment Editing Guide

## Overview

The dairy management system now supports editing payments that were distributed across multiple months. This feature allows you to:

1. **View existing allocations** when editing a multi-month payment
2. **Change the payment amount** and have it redistributed
3. **Change which months** receive the payment
4. **Convert between single-month and multi-month** payments

## How Multi-Month Payments Work

When you create a payment and select "Distribute across multiple months":
- The payment is allocated across the selected unpaid months
- Each allocation is stored separately in the `PaymentAllocation` model
- The payment itself has `payment_for_month` and `payment_for_year` set to `NULL`
- Monthly balances are automatically updated to reflect the allocations

## Editing Multi-Month Payments

### Accessing the Edit Form

1. **From Customer Detail Page:**
   - Navigate to a customer's detail page
   - In the "Recent Payments" section, look for payments with a "Multi-month" badge
   - Click the edit button (pencil icon) next to the payment

2. **From Payment List:**
   - Go to the payments list
   - Find the payment you want to edit
   - Click the edit button

### Understanding the Edit Interface

When editing a multi-month payment, you'll see:

1. **Current Payment Allocations Section:**
   - Shows a table of current month allocations
   - Displays which months currently receive portions of the payment
   - Shows the amount allocated to each month
   - Provides clear instructions on how to make changes

2. **Multi-Month Distribution Checkbox:**
   - Pre-checked for existing multi-month payments
   - Can be unchecked to convert to a single-month payment
   - When checked, shows the month selection interface

### Making Changes

#### Option 1: Change Payment Amount Only
1. Modify the amount field
2. Keep "Distribute across multiple months" checked
3. Check the same months that were previously selected
4. Save the payment
5. The system will redistribute the new amount across the selected months

#### Option 2: Change Which Months Get the Payment
1. Keep the amount the same (or change it)
2. Ensure "Distribute across multiple months" is checked
3. Select different months from the unpaid months table
4. Save the payment
5. The payment will be reallocated to the newly selected months

#### Option 3: Convert to Single-Month Payment
1. Uncheck "Distribute across multiple months"
2. Select the specific month and year in the dropdown fields
3. Save the payment
4. All previous allocations will be removed
5. The full payment amount will be assigned to the selected single month

## Important Notes

### Automatic Recalculation
- When you save changes, the system automatically:
  - Removes old allocations
  - Creates new allocations based on your selections
  - Recalculates monthly balances for the customer
  - Updates payment status for affected months

### Distribution Logic
- Payments are distributed to months in chronological order (oldest first)
- Each month gets allocated the minimum of:
  - The remaining payment amount
  - The amount owed for that month
- If payment amount exceeds the total owed for selected months, the excess remains unallocated

### Visual Indicators
- **Multi-month badge:** Payments distributed across multiple months show a blue "Multi-month" badge
- **Single-month badge:** Payments for specific months show a green badge with the month/year
- **General badge:** Payments without specific month assignment show a gray "General" badge

## Navigation Improvements

- **Contextual navigation:** When editing payments from a customer detail page, you'll return to that customer page after saving
- **Cancel buttons:** Lead back to the appropriate page (customer detail or payment list)
- **Back buttons:** Show "Back to Customer" or "Back to List" depending on your starting point

## Troubleshooting

### Payment Not Showing as Multi-Month
- Check if the payment has allocations in the database
- Verify that `payment_for_month` and `payment_for_year` are NULL for the payment

### Changes Not Reflected
- Monthly balances are recalculated automatically, but may take a moment to update
- Try refreshing the customer detail page to see updated balances

### Cannot Edit Allocations
- Ensure the payment exists and you have proper permissions
- Check that the customer still exists and has unpaid months available

## Technical Details

### Database Structure
- **Payment model:** Stores the main payment record
- **PaymentAllocation model:** Stores individual month allocations
- **MonthlyBalance model:** Tracks calculated balances per month

### Cascade Behavior
- Deleting a payment automatically removes all its allocations
- Editing a payment recreates allocations from scratch
- Monthly balances are automatically recalculated after changes

This enhanced editing system provides flexibility while maintaining data integrity and proper audit trails for all payment modifications.

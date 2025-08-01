# PythonAnywhere Deployment Fix Guide

## Step 1: Set Environment Variable
In your PythonAnywhere bash console, run:
```bash
echo 'export PYTHONANYWHERE=1' >> ~/.bashrc
source ~/.bashrc
```

## Step 2: Install Required Packages
In your PythonAnywhere bash console, activate your virtual environment and install packages:
```bash
# Navigate to your project
cd ~/dairy_manager

# Activate virtual environment
source venv/bin/activate

# Install required packages
pip install mysqlclient==2.2.0
pip install reportlab==4.1.0
pip install xlwt==1.3.0
pip install PyPDF2==3.0.1

# Or install all from requirements.txt
pip install -r requirements.txt
```

## Step 3: Create and Configure Database
1. Go to PythonAnywhere Dashboard > Databases
2. Create a new MySQL database named `mr0264$dairy_manager`
3. Set the password to `Abhimay@5204`

## Step 4: Run Database Migrations
In your PythonAnywhere bash console:
```bash
cd ~/dairy_manager
source venv/bin/activate

# Set environment variable for this session
export PYTHONANYWHERE=1

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

## Step 5: Update WSGI Configuration
In your PythonAnywhere Web tab, edit your WSGI file to include:

```python
import os
import sys

# Set the environment variable
os.environ['PYTHONANYWHERE'] = '1'

# Add your project directory to Python path
path = '/home/mr0264/dairy_manager'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'dairy_manager.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## Step 6: Collect Static Files
```bash
cd ~/dairy_manager
source venv/bin/activate
export PYTHONANYWHERE=1
python manage.py collectstatic --noinput
```

## Step 7: Reload Web App
Go to PythonAnywhere Web tab and click "Reload" button.

## Troubleshooting

### If you get "Table doesn't exist" errors:
```bash
export PYTHONANYWHERE=1
python manage.py migrate --run-syncdb
```

### If you get permission errors:
```bash
chmod 644 ~/dairy_manager/db.sqlite3  # if using SQLite for testing
```

### Check error logs:
- Go to PythonAnywhere Web tab
- Click on "Error log" to see detailed error messages

### Test database connection:
```bash
cd ~/dairy_manager
source venv/bin/activate
export PYTHONANYWHERE=1
python manage.py shell

# In Django shell:
from django.db import connection
cursor = connection.cursor()
cursor.execute("SHOW TABLES;")
print(cursor.fetchall())
```

## Expected Database Tables After Migration:
- auth_user
- auth_group
- auth_permission
- django_content_type
- django_session
- dairy_app_area
- dairy_app_customer
- dairy_app_milktype
- dairy_app_sale
- dairy_app_payment
- dairy_app_monthlybalance
- dairy_app_paymentallocation

## URL to Test:
After deployment, test your app at:
https://mr0264.pythonanywhere.com/dairy/

## Common Issues and Solutions:

1. **ModuleNotFoundError: No module named 'reportlab'**
   - Run: `pip install reportlab==4.1.0`

2. **ModuleNotFoundError: No module named 'xlwt'**
   - Run: `pip install xlwt==1.3.0`

3. **django.core.exceptions.ImproperlyConfigured: Error loading MySQLdb module**
   - Run: `pip install mysqlclient==2.2.0`

4. **Table 'mr0264$dairy_manager.auth_user' doesn't exist**
   - Run migrations as shown in Step 4

5. **Can't connect to MySQL server**
   - Check database name, username, and password in settings.py
   - Ensure PYTHONANYWHERE environment variable is set

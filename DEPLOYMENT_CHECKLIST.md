# PythonAnywhere Deployment Checklist and Troubleshooting Guide

## Overview
Your Django dairy management app is having deployment issues on PythonAnywhere. Here's a step-by-step guide to fix all the problems.

## Problems Identified:
1. ❌ MySQLdb module missing (`mysqlclient` not installed)
2. ❌ ReportLab module missing
3. ❌ xlwt module missing  
4. ❌ Database tables don't exist (migrations not run)
5. ❌ Environment variables not set

## Step-by-Step Fix:

### 1. Set Environment Variables
```bash
# In PythonAnywhere bash console
echo 'export PYTHONANYWHERE=1' >> ~/.bashrc
source ~/.bashrc
```

### 2. Install Missing Packages
```bash
cd ~/dairy_manager
source venv/bin/activate

# Install all required packages
pip install mysqlclient==2.2.0
pip install reportlab==4.1.0
pip install xlwt==1.3.0
pip install PyPDF2==3.0.1

# Or install everything from requirements.txt
pip install -r requirements.txt
```

### 3. Database Setup
1. **Create MySQL Database:**
   - Go to PythonAnywhere Dashboard → Databases
   - Create database: `mr0264$dairy_manager`
   - Set password: `Abhimay@5204`

2. **Run Migrations:**
```bash
cd ~/dairy_manager
source venv/bin/activate
export PYTHONANYWHERE=1

python manage.py makemigrations
python manage.py migrate
```

### 4. Update WSGI File
Edit `/var/www/mr0264_pythonanywhere_com_wsgi.py`:

```python
import os
import sys

# Set environment variable for PythonAnywhere
os.environ['PYTHONANYWHERE'] = '1'

# Add project to Python path
path = '/home/mr0264/dairy_manager'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'dairy_manager.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 5. Collect Static Files
```bash
cd ~/dairy_manager
source venv/bin/activate
export PYTHONANYWHERE=1
python manage.py collectstatic --noinput
```

### 6. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 7. Reload Web App
- Go to PythonAnywhere Web tab
- Click "Reload" button

## Testing Commands

### Test Database Connection:
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

### Check Installed Packages:
```bash
pip list | grep -E "(mysqlclient|reportlab|xlwt|PyPDF2)"
```

### Test URL:
Visit: `https://mr0264.pythonanywhere.com/dairy/`

## Expected Database Tables:
After successful migration, you should see these tables:
- `auth_user`
- `auth_group` 
- `auth_permission`
- `django_content_type`
- `django_session`
- `dairy_app_area`
- `dairy_app_customer`
- `dairy_app_milktype`
- `dairy_app_sale`
- `dairy_app_payment`
- `dairy_app_monthlybalance`
- `dairy_app_paymentallocation`

## Common Error Solutions:

### Error: "No module named 'MySQLdb'"
**Solution:** `pip install mysqlclient==2.2.0`

### Error: "No module named 'reportlab'"
**Solution:** `pip install reportlab==4.1.0`

### Error: "No module named 'xlwt'"
**Solution:** `pip install xlwt==1.3.0`

### Error: "Table 'auth_user' doesn't exist"
**Solution:** 
```bash
export PYTHONANYWHERE=1
python manage.py migrate
```

### Error: "Can't connect to MySQL server"
**Causes:**
- Database not created
- Wrong password
- Environment variable not set

**Solutions:**
1. Create database in PythonAnywhere dashboard
2. Check password in settings.py
3. Set `PYTHONANYWHERE=1` environment variable

### Error: "DisallowedHost"
**Solution:** Check `ALLOWED_HOSTS` in settings.py includes `'mr0264.pythonanywhere.com'`

## Code Changes Made:
1. ✅ Added conditional imports for reportlab and PyPDF2
2. ✅ Added mysqlclient to requirements.txt
3. ✅ Added error handling for missing packages
4. ✅ Fixed import errors in models.py and views.py

## Final Verification:
1. Check error logs in PythonAnywhere Web tab
2. Visit your app URL
3. Try logging in
4. Test basic functionality (customers, sales, payments)

## Support:
If you still encounter issues:
1. Check PythonAnywhere error logs
2. Run the test commands above
3. Verify all packages are installed
4. Ensure environment variable is set

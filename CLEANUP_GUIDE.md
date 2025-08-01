# Dairy Manager Project Cleanup

## Files and Folders to Remove for Disk Space Optimization

This document explains what can be safely removed from the project to reduce disk usage on PythonAnywhere.

## 🗑️ Safe to Remove (Development/Testing Files):

### 1. Duplicate Virtual Environments
- `new_venv/` - Duplicate virtual environment (keep only `venv/`)

### 2. Standalone Scripts (No longer needed after Django management commands)
- `assign_customers_to_areas.py` - Replaced by Django management commands
- `create_areas.py` - Replaced by Django management commands  
- `create_template_pdf.py` - Development testing script
- `debug_unpaid_months.py` - Debug script, not needed in production
- `generate_sales.py` - Replaced by Django management commands
- `manage_customer_areas.py` - Replaced by Django management commands
- `populate_areas_customers_sales.py` - Replaced by Django management commands
- `populate_customers.py` - Replaced by Django management commands
- `reset_and_generate_data.py` - Development script
- `reset_and_populate_sales.py` - Development script

### 3. Documentation Files (Keep in Git, Remove from Production)
- `CUSTOMER_AREA_SCRIPTS_README.md`
- `CUSTOMER_NAVIGATION_FEATURE.md`
- `DEMO_DATA_GUIDE.md`
- `DEPLOYMENT_CHECKLIST.md`
- `deploy_pythonanywhere.md`
- `LAST_SIX_MONTHS_FEATURE.md`
- `MULTI_MONTH_PAYMENT_EDITING.md`
- `PYTHONANYWHERE_DEPLOYMENT.md`
- `PYTHONANYWHERE_PDF_FIX.md`
- `README.md`
- `TESTING_RESULTS_SUMMARY.md`

### 4. Development Files
- `.vscode/` - VS Code settings (if exists)
- `.git/` - Git repository (keep locally, not needed on production)
- `django_error.log` - Log file
- `deploy.sh` - Deployment script

### 5. Environment Files (Keep only production version)
- `.env.example` - Example file
- `pythonanywhere.env.example` - Example file

## ⚠️ Keep These Essential Files:

### Core Application
- `manage.py`
- `dairy_app/` (entire directory)
- `dairy_manager/` (settings directory)
- `requirements.txt`
- `db.sqlite3` (database)

### Production Configuration
- `pythonanywhere.env` (production environment file)
- `new_bill.pdf` (PDF template)

### Static/Template Files
- `static/` (if contains actual static files used by app)
- `templates/` (if contains actual templates used by app)
- `locale/` (translation files)

### Virtual Environment (Choose one)
- Keep either `venv/` OR `new_venv/` (not both)

## 📦 Optimize Requirements.txt

Remove unused packages from requirements.txt:
- Remove packages only used for development/testing
- Keep only production-necessary packages

## 🛠️ Cleanup Commands

Run these commands on PythonAnywhere:

```bash
# Navigate to project directory
cd ~/dairy_manager

# Remove duplicate virtual environment
rm -rf new_venv/

# Remove standalone scripts
rm -f assign_customers_to_areas.py create_areas.py create_template_pdf.py
rm -f debug_unpaid_months.py generate_sales.py manage_customer_areas.py
rm -f populate_areas_customers_sales.py populate_customers.py
rm -f reset_and_generate_data.py reset_and_populate_sales.py

# Remove documentation files  
rm -f *.md
rm -f deploy.sh
rm -f django_error.log

# Remove development files
rm -rf .vscode/
rm -rf .git/
rm -f .env.example pythonanywhere.env.example

# Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete

# Clean virtual environment cache (if using pip cache)
pip cache purge
```

## 📊 Expected Space Savings:

- Virtual environment duplication: ~100-300MB
- Git repository: ~50-100MB  
- Python cache files: ~10-50MB
- Standalone scripts: ~1-5MB
- Documentation: ~1-5MB
- **Total Expected Savings: ~160-460MB**

## ⚡ After Cleanup:

1. Test that the application still works
2. Ensure all required dependencies are in requirements.txt
3. Verify PDF generation still works
4. Check that Django management commands work properly

#!/bin/bash

# Dairy Manager Cleanup Script for PythonAnywhere
# This script removes unnecessary files to save disk space

echo "🚀 Starting Dairy Manager Project Cleanup..."

# Make sure we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Not in Django project directory. Please cd to your project directory first."
    exit 1
fi

echo "📍 Current directory: $(pwd)"

# Backup requirements.txt before cleanup
echo "💾 Backing up current requirements.txt..."
cp requirements.txt requirements_backup.txt

echo "🗑️ Removing duplicate virtual environment..."
if [ -d "new_venv" ]; then
    rm -rf new_venv/
    echo "✅ Removed new_venv/"
else
    echo "ℹ️ new_venv/ not found, skipping..."
fi

echo "🗑️ Removing standalone scripts..."
scripts_to_remove=(
    "assign_customers_to_areas.py"
    "create_areas.py" 
    "create_template_pdf.py"
    "debug_unpaid_months.py"
    "generate_sales.py"
    "manage_customer_areas.py"
    "populate_areas_customers_sales.py"
    "populate_customers.py"
    "reset_and_generate_data.py"
    "reset_and_populate_sales.py"
)

for script in "${scripts_to_remove[@]}"; do
    if [ -f "$script" ]; then
        rm -f "$script"
        echo "✅ Removed $script"
    fi
done

echo "🗑️ Removing documentation files..."
docs_to_remove=(
    "CUSTOMER_AREA_SCRIPTS_README.md"
    "CUSTOMER_NAVIGATION_FEATURE.md"
    "DEMO_DATA_GUIDE.md"
    "DEPLOYMENT_CHECKLIST.md"
    "deploy_pythonanywhere.md"
    "LAST_SIX_MONTHS_FEATURE.md"
    "MULTI_MONTH_PAYMENT_EDITING.md"
    "PYTHONANYWHERE_DEPLOYMENT.md"
    "PYTHONANYWHERE_PDF_FIX.md"
    "README.md"
    "TESTING_RESULTS_SUMMARY.md"
    "CLEANUP_GUIDE.md"
)

for doc in "${docs_to_remove[@]}"; do
    if [ -f "$doc" ]; then
        rm -f "$doc"
        echo "✅ Removed $doc"
    fi
done

echo "🗑️ Removing development files..."
dev_files=(
    "deploy.sh"
    "django_error.log"
    ".env.example"
    "pythonanywhere.env.example"
)

for file in "${dev_files[@]}"; do
    if [ -f "$file" ]; then
        rm -f "$file"
        echo "✅ Removed $file"
    fi
done

echo "🗑️ Removing development directories..."
if [ -d ".vscode" ]; then
    rm -rf .vscode/
    echo "✅ Removed .vscode/"
fi

if [ -d ".git" ]; then
    rm -rf .git/
    echo "✅ Removed .git/"
fi

echo "🧹 Cleaning Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
find . -name "*.pyo" -delete 2>/dev/null
echo "✅ Cleaned Python cache files"

echo "📦 Optimizing requirements.txt..."
if [ -f "requirements_optimized.txt" ]; then
    mv requirements_optimized.txt requirements.txt
    echo "✅ Updated requirements.txt with optimized version"
else
    echo "ℹ️ Optimized requirements file not found, keeping original"
fi

echo "🧹 Cleaning pip cache..."
pip cache purge 2>/dev/null || echo "ℹ️ pip cache purge not available or already clean"

echo ""
echo "✅ Cleanup completed!"
echo ""
echo "📊 Summary of actions:"
echo "  • Removed duplicate virtual environment"
echo "  • Removed standalone scripts (replaced by Django management commands)"
echo "  • Removed documentation files"
echo "  • Removed development files and directories"
echo "  • Cleaned Python cache files"
echo "  • Optimized requirements.txt"
echo ""
echo "🔍 Next steps:"
echo "  1. Test your application: python manage.py runserver"
echo "  2. Test PDF generation: Visit a customer bill URL"
echo "  3. Check Django management commands: python manage.py populate_demo_data --help"
echo "  4. If everything works, you can delete requirements_backup.txt"
echo ""
echo "💾 Backup files created:"
echo "  • requirements_backup.txt (your original requirements.txt)"

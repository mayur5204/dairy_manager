# Dairy Manager Cleanup Script for Windows/PowerShell
# This script removes unnecessary files to save disk space

Write-Host "🚀 Starting Dairy Manager Project Cleanup..." -ForegroundColor Green

# Make sure we're in the right directory
if (!(Test-Path "manage.py")) {
    Write-Host "❌ Error: Not in Django project directory. Please cd to your project directory first." -ForegroundColor Red
    exit 1
}

Write-Host "📍 Current directory: $(Get-Location)" -ForegroundColor Blue

# Backup requirements.txt before cleanup
Write-Host "💾 Backing up current requirements.txt..." -ForegroundColor Yellow
Copy-Item "requirements.txt" "requirements_backup.txt"

Write-Host "🗑️ Removing duplicate virtual environment..." -ForegroundColor Yellow
if (Test-Path "new_venv") {
    Remove-Item -Recurse -Force "new_venv"
    Write-Host "✅ Removed new_venv/" -ForegroundColor Green
} else {
    Write-Host "ℹ️ new_venv/ not found, skipping..." -ForegroundColor Gray
}

Write-Host "🗑️ Removing standalone scripts..." -ForegroundColor Yellow
$scriptsToRemove = @(
    "assign_customers_to_areas.py",
    "create_areas.py",
    "create_template_pdf.py", 
    "debug_unpaid_months.py",
    "generate_sales.py",
    "manage_customer_areas.py",
    "populate_areas_customers_sales.py",
    "populate_customers.py",
    "reset_and_generate_data.py",
    "reset_and_populate_sales.py"
)

foreach ($script in $scriptsToRemove) {
    if (Test-Path $script) {
        Remove-Item $script
        Write-Host "✅ Removed $script" -ForegroundColor Green
    }
}

Write-Host "🗑️ Removing documentation files..." -ForegroundColor Yellow
$docsToRemove = @(
    "CUSTOMER_AREA_SCRIPTS_README.md",
    "CUSTOMER_NAVIGATION_FEATURE.md",
    "DEMO_DATA_GUIDE.md",
    "DEPLOYMENT_CHECKLIST.md",
    "deploy_pythonanywhere.md",
    "LAST_SIX_MONTHS_FEATURE.md",
    "MULTI_MONTH_PAYMENT_EDITING.md",
    "PYTHONANYWHERE_DEPLOYMENT.md",
    "PYTHONANYWHERE_PDF_FIX.md",
    "README.md",
    "TESTING_RESULTS_SUMMARY.md",
    "CLEANUP_GUIDE.md"
)

foreach ($doc in $docsToRemove) {
    if (Test-Path $doc) {
        Remove-Item $doc
        Write-Host "✅ Removed $doc" -ForegroundColor Green
    }
}

Write-Host "🗑️ Removing development files..." -ForegroundColor Yellow
$devFiles = @(
    "deploy.sh",
    "django_error.log",
    ".env.example",
    "pythonanywhere.env.example"
)

foreach ($file in $devFiles) {
    if (Test-Path $file) {
        Remove-Item $file
        Write-Host "✅ Removed $file" -ForegroundColor Green
    }
}

Write-Host "🗑️ Removing development directories..." -ForegroundColor Yellow
if (Test-Path ".vscode") {
    Remove-Item -Recurse -Force ".vscode"
    Write-Host "✅ Removed .vscode/" -ForegroundColor Green
}

Write-Host "🧹 Cleaning Python cache files..." -ForegroundColor Yellow
Get-ChildItem -Recurse -Directory -Name "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Name "*.pyc" | Remove-Item
Get-ChildItem -Recurse -Name "*.pyo" | Remove-Item
Write-Host "✅ Cleaned Python cache files" -ForegroundColor Green

Write-Host "📦 Optimizing requirements.txt..." -ForegroundColor Yellow
if (Test-Path "requirements_optimized.txt") {
    Move-Item "requirements_optimized.txt" "requirements.txt" -Force
    Write-Host "✅ Updated requirements.txt with optimized version" -ForegroundColor Green
} else {
    Write-Host "ℹ️ Optimized requirements file not found, keeping original" -ForegroundColor Gray
}

Write-Host ""
Write-Host "✅ Cleanup completed!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Summary of actions:" -ForegroundColor Blue
Write-Host "  • Removed duplicate virtual environment"
Write-Host "  • Removed standalone scripts (replaced by Django management commands)"
Write-Host "  • Removed documentation files"
Write-Host "  • Removed development files and directories"
Write-Host "  • Cleaned Python cache files"
Write-Host "  • Optimized requirements.txt"
Write-Host ""
Write-Host "🔍 Next steps:" -ForegroundColor Blue
Write-Host "  1. Test your application: python manage.py runserver"
Write-Host "  2. Test PDF generation: Visit a customer bill URL"
Write-Host "  3. Check Django management commands: python manage.py populate_demo_data --help"
Write-Host "  4. If everything works, you can delete requirements_backup.txt"
Write-Host ""
Write-Host "💾 Backup files created:" -ForegroundColor Yellow
Write-Host "  • requirements_backup.txt (your original requirements.txt)"

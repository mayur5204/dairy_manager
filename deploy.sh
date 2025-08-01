#!/bin/bash

# PythonAnywhere Deployment Script
# Run this script in your PythonAnywhere bash console

echo "Starting PythonAnywhere deployment..."

# Set environment variable
export PYTHONANYWHERE=1
echo 'export PYTHONANYWHERE=1' >> ~/.bashrc

# Navigate to project directory
cd ~/dairy_manager

# Activate virtual environment
source venv/bin/activate

echo "Installing required packages..."
# Install required packages
pip install mysqlclient==2.2.0
pip install reportlab==4.1.0
pip install xlwt==1.3.0
pip install PyPDF2==3.0.1

echo "Running database migrations..."
# Run migrations
python manage.py makemigrations
python manage.py migrate

echo "Collecting static files..."
# Collect static files
python manage.py collectstatic --noinput

echo "Creating superuser (optional - you can skip this)..."
# Uncomment the next line if you want to create a superuser
# python manage.py createsuperuser

echo "Deployment completed!"
echo "Don't forget to:"
echo "1. Update your WSGI file in PythonAnywhere Web tab"
echo "2. Reload your web app"
echo "3. Check the error logs if something doesn't work"

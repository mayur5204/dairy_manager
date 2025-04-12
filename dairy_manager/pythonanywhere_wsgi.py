"""
WSGI configuration for PythonAnywhere.
This file should be used in the PythonAnywhere WSGI configuration.
"""

import os
import sys
from pathlib import Path

# Add the project directory to the Python path
path = '/home/mr0264/dairy-manager'
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variables
os.environ['DJANGO_SETTINGS_MODULE'] = 'dairy_manager.settings'
os.environ['PYTHONANYWHERE'] = 'True'  # Set this explicitly

# Add python-dotenv support if needed
try:
    from dotenv import load_dotenv
    # Load environment variables from .env file if it exists
    env_path = Path(path) / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

# Create application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
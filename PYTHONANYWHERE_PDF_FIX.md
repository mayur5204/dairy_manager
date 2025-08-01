# PyPDF2 Installation Fix for PythonAnywhere

## Problem
When trying to generate customer bills, you get the error:
```
ModuleNotFoundError: No module named 'PyPDF2'
```

This happens because PyPDF2 is not installed in your PythonAnywhere virtual environment, even though it's listed in `requirements.txt`.

## Solution

### Method 1: Install via PythonAnywhere Console (Recommended)

1. **Open a Bash Console** in your PythonAnywhere dashboard
2. **Navigate to your project directory**:
   ```bash
   cd dairy_manager
   ```
3. **Activate your virtual environment**:
   ```bash
   source venv/bin/activate
   ```
4. **Install PyPDF2**:
   ```bash
   pip install PyPDF2==3.0.1
   ```

### Method 2: Reinstall all requirements

1. **Open a Bash Console** in your PythonAnywhere dashboard
2. **Navigate to your project directory**:
   ```bash
   cd dairy_manager
   ```
3. **Activate your virtual environment**:
   ```bash
   source venv/bin/activate
   ```
4. **Install all requirements**:
   ```bash
   pip install -r requirements.txt
   ```

### Method 3: Alternative PDF Library

If PyPDF2 continues to cause issues, you can replace it with `pypdf` (the newer version):

1. **Update requirements.txt** - Replace:
   ```
   PyPDF2==3.0.1
   ```
   With:
   ```
   pypdf==4.0.2
   ```

2. **Update views.py imports** - Replace:
   ```python
   from PyPDF2 import PdfReader, PdfWriter
   ```
   With:
   ```python
   from pypdf import PdfReader, PdfWriter
   ```

## Verification

After installation, verify it works:

1. **Test the import in Python console**:
   ```bash
   python3
   >>> from PyPDF2 import PdfReader, PdfWriter
   >>> print("PyPDF2 is working!")
   >>> exit()
   ```

2. **Test bill generation** by visiting:
   ```
   https://yourdomain.pythonanywhere.com/en/dairy/customers/[customer_id]/bill/?month=7&year=2025
   ```

## Current Fallback Behavior

The code has been updated to handle missing PyPDF2 gracefully:
- If PyPDF2 is not available, users will see an error message
- They will be redirected back to the customer detail page
- No application crash will occur

## Why This Happens

This typically occurs when:
1. Virtual environment wasn't activated during pip install
2. Requirements.txt wasn't installed properly during deployment
3. Different Python/pip versions between local and production
4. PythonAnywhere package cache issues

## Prevention

To prevent this in future deployments:
1. Always activate virtual environment before installing packages
2. Use `pip freeze > requirements.txt` to ensure all dependencies are captured
3. Test critical features after deployment
4. Consider using `pip install --upgrade --force-reinstall` for problematic packages

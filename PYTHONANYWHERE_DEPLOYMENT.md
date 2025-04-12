# Deploying Dairy Management Application to PythonAnywhere

This document provides step-by-step instructions for deploying your dairy management application to PythonAnywhere.

## Step 1: Create a PythonAnywhere Account

1. Go to [PythonAnywhere.com](https://www.pythonanywhere.com/) and sign up for an account
2. The free tier is sufficient to start, but a paid account will provide better performance and a custom domain

## Step 2: Upload Your Code

### Option A: Using GitHub (Recommended)

If your code is already in a GitHub repository:

1. Log in to PythonAnywhere and open a Bash console from the dashboard
2. Clone your repository:
   ```bash
   mkdir -p ~/dairy-manager
   cd ~/dairy-manager
   git clone https://github.com/yourusername/dairy-manager.git .
   ```

### Option B: Manual Upload

If your code is not in a repository:

1. Create a zip archive of your `dairy_manager` directory (excluding the `dairy_env` folder)
2. Log in to PythonAnywhere and go to the "Files" tab
3. Create a new directory called `dairy-manager`
4. Navigate into this directory and upload the zip file
5. Open a Bash console and extract the files:
   ```bash
   cd ~/dairy-manager
   unzip your-zip-file.zip
   rm your-zip-file.zip  # Remove the zip file after extraction
   ```

## Step 3: Set Up the Database

1. Go to the "Databases" tab in PythonAnywhere
2. Create a new MySQL database (Note: Free tier includes MySQL databases)
3. Note your database name format: `yourusername$dairy_manager`
4. Set a secure password and make note of it

## Step 4: Set Up a Virtual Environment

In the PythonAnywhere Bash console:

```bash
cd ~/dairy-manager
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 5: Configure Environment Variables

1. Create a `.env` file based on the `pythonanywhere.env` template:

```bash
cd ~/dairy-manager
cp pythonanywhere.env .env
```

2. Edit the `.env` file to update your actual database password:

```bash
nano .env
```

Make sure to change the `DATABASE_PASSWORD` value to the password you set for your MySQL database.

## Step 6: Create a Web App

1. Go to the "Web" tab in PythonAnywhere
2. Click "Add a new web app"
3. Select your domain name (with free accounts, it will be yourusername.pythonanywhere.com)
4. Choose "Manual configuration" (not "Django")
5. Select Python 3.12

## Step 7: Configure the Web App

On the web app configuration page:

1. Set the virtual environment path:
   ```
   /home/yourusername/dairy-manager/venv
   ```

2. Modify the WSGI configuration file by clicking on the link and replacing its contents with the content of your `pythonanywhere_wsgi.py` file. Be sure to:
   - Update the path to match your PythonAnywhere username
   - Make sure the import statements match your project structure

3. Configure static files:
   - URL: `/static/`
   - Directory: `/home/yourusername/dairy-manager/staticfiles`

## Step 8: Run Django Management Commands

In the Bash console:

```bash
cd ~/dairy-manager
source venv/bin/activate

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser
```

## Step 9: Reload Your Web App

1. Go back to the "Web" tab
2. Click the "Reload" button for your web app

## Step 10: Visit Your Site

Your site should now be live at:
```
https://yourusername.pythonanywhere.com
```

## Troubleshooting

### Database Connection Issues

If you have issues connecting to the database:

1. Make sure your `DATABASES` configuration in `settings.py` is correct
2. Check that the `DATABASE_PASSWORD` in your `.env` file matches your MySQL database password
3. Verify that the `PYTHONANYWHERE` environment variable is set to `True` in your `.env` file

### Static Files Not Loading

1. Check that your `STATIC_URL` and `STATIC_ROOT` settings are correct
2. Run `python manage.py collectstatic --noinput` again
3. Make sure the static files are configured correctly in the PythonAnywhere web app settings

### 500 Internal Server Errors

1. Check the error logs in the "Web" tab
2. Temporarily set `DEBUG=True` in your `.env` file and reload the app to see detailed error messages

### WhiteNoise Issues

If you have issues with static files and WhiteNoise:

1. Check that `whitenoise.middleware.WhiteNoiseMiddleware` is in your `MIDDLEWARE` setting
2. Verify that `STATICFILES_STORAGE` is properly configured
3. Make sure WhiteNoise is installed in your virtual environment
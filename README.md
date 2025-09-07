# 🥛 Dairy Management System

A comprehensive web-based dairy management system built with Django to streamline milk delivery operations, customer management, and financial tracking for dairy businesses.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/django-5.2-green.svg)](https://djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🌟 Features

### 📊 Customer & Area Management
- **Customer Registration**: Complete customer profiles with contact information and delivery preferences
- **Area-wise Organization**: Customers grouped by delivery areas with route optimization
- **Delivery Order Sequencing**: Efficient route planning with customizable delivery sequences
- **Multi-milk Type Support**: Configure different milk types (Cow, Buffalo, etc.) per customer

### 💰 Sales & Inventory Tracking
- **Daily Sales Recording**: Quick and efficient milk sales entry.
- **Multi-milk Type Sales**: Handle different milk varieties with automatic rate calculation
- **Real-time Inventory**: Track daily milk sales and delivery quantities
- **Quick Customer Search**: Fast customer selection with auto-complete functionality

### 💳 Advanced Payment Management
- **Monthly Balance Calculation**: Automated monthly balance tracking and calculation
- **Multi-month Payment Distribution**: Intelligent payment allocation across multiple months
- **Payment History**: Comprehensive payment tracking with detailed allocation records
- **Smart Payment Allocation**: Automatic distribution starting from oldest unpaid months

### 📄 Reporting & Analytics
- **PDF Bill Generation**: Professional bills using ReportLab with custom templates
- **Excel Export**: Data export functionality for external analysis
- **Monthly Consumption Reports**: Customer-wise consumption analysis
- **Area-wise Sales Reports**: Territory-based sales analytics with filtering
- **Payment Status Tracking**: Detailed payment history and pending balance reports

### 🌐 Multi-language Support
- **Internationalization**: Support for English, Hindi, and Marathi
- **Localized Content**: Region-specific formatting and currency display
- **Devanagari Font Support**: Native script support for Indian languages

## 🚀 Technology Stack

- **Backend**: Django 5.2, Python 3.8+
- **Database**: MySQL (Production), SQLite (Development)
- **Frontend**: Bootstrap 4, JavaScript, jQuery
- **PDF Generation**: ReportLab, PyPDF2
- **Data Export**: xlwt (Excel format)
- **Server**: Gunicorn, WhiteNoise
- **Styling**: Crispy Forms, Bootstrap 4

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- MySQL (for production) or SQLite (for development)
- Git

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/mayur5204/dairy_manager.git
   cd dairy_manager
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Create a `.env` file in the project root:
   ```env
   DJANGO_SECRET_KEY=your-secret-key-here
   DJANGO_DEBUG=True
   
   # For MySQL (optional)
   DATABASE_URL=mysql://username:password@localhost/dairy_manager
   
   # Security settings for production
   DJANGO_SECURE_SSL_REDIRECT=False
   DJANGO_SESSION_COOKIE_SECURE=False
   DJANGO_CSRF_COOKIE_SECURE=False
   ```

5. **Database Setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Load Demo Data (Optional)**
   ```bash
   python manage.py populate_demo_data
   ```

8. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

Visit `http://127.0.0.1:8000` to access the application.

## 🌐 Production Deployment

### PythonAnywhere Deployment

1. **Environment Variables**
   Set the following environment variables:
   ```bash
   PYTHONANYWHERE=1
   DJANGO_SECRET_KEY=your-production-secret-key
   DJANGO_DEBUG=False
   DJANGO_SECURE_SSL_REDIRECT=True
   DJANGO_SESSION_COOKIE_SECURE=True
   DJANGO_CSRF_COOKIE_SECURE=True
   ```

2. **Database Configuration**
   The app automatically configures MySQL for PythonAnywhere when `PYTHONANYWHERE=1` is set.

3. **Static Files**
   ```bash
   python manage.py collectstatic --noinput
   ```

4. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

### Other Hosting Platforms

For deployment on other platforms, ensure you:
- Set appropriate environment variables
- Configure database settings
- Set up static file serving
- Configure proper security settings

## 📋 Usage Guide

### Getting Started

1. **Initial Setup**
   - Create areas for your delivery routes
   - Add customers with their delivery areas
   - Configure milk types and rates

2. **Daily Operations**
   - Record daily milk sales for customers
   - Process customer payments
   - Generate monthly bills

3. **Monthly Tasks**
   - Review monthly balances
   - Generate customer reports
   - Export data for accounting

### Key Workflows

#### Recording Sales
1. Navigate to Sales → Add Sale
2. Select customer and date
3. Enter milk quantities for different types
4. Save the sale record

#### Processing Payments
1. Go to customer detail page
2. Click "New Payment"
3. Enter payment amount
4. Choose single month or multi-month distribution
5. For multi-month: select months to allocate payment

#### Generating Bills
1. Open customer detail page
2. Select month and year for bill
3. Click "Generate Bill" 
4. PDF bill downloads automatically

## 🛠️ Management Commands

The system includes several useful management commands:

```bash
# Check PDF dependencies
python manage.py check_pdf_dependencies

# Populate demo data
python manage.py populate_demo_data

# Update monthly balances for all customers
python manage.py update_monthly_balances

# Enable global data access for superusers
python manage.py enable_global_data_access
```

## 📱 API Endpoints

The system provides AJAX endpoints for dynamic functionality:

- `/ajax/get-milk-types/` - Get milk types for a specific customer
- `/ajax/get-all-milk-types/` - Get all available milk types
- Customer search and selection APIs

## 🔧 Configuration

### Settings Overview

Key configuration options in `settings.py`:

- **Multi-language Support**: Configure `LANGUAGES` and `LOCALE_PATHS`
- **Database**: Automatic MySQL/SQLite switching based on environment
- **Static Files**: WhiteNoise configuration for production
- **Security**: Environment-based security settings
- **Logging**: Comprehensive logging for debugging and monitoring

### Customization

The system is designed to be easily customizable:

- **Templates**: Modify HTML templates in `templates/dairy_app/`
- **Models**: Extend models in `dairy_app/models.py`
- **Forms**: Customize forms in `dairy_app/forms.py`
- **Views**: Add new functionality in `dairy_app/views.py`

## 🗂️ Project Structure

```
dairy_manager/
├── dairy_app/              # Main application
│   ├── management/         # Custom management commands
│   ├── migrations/         # Database migrations
│   ├── templates/          # HTML templates
│   ├── static/            # Static files
│   ├── templatetags/      # Custom template tags
│   ├── models.py          # Database models
│   ├── views.py           # Application views
│   ├── forms.py           # Django forms
│   ├── urls.py            # URL configurations
│   └── admin.py           # Admin interface
├── dairy_manager/          # Project settings
│   ├── settings.py        # Django settings
│   ├── urls.py            # Main URL configuration
│   └── wsgi.py            # WSGI application
├── templates/             # Global templates
├── static/               # Global static files
├── locale/               # Translation files
├── requirements.txt      # Python dependencies
└── manage.py            # Django management script
```

## 🔍 Testing

Run the test suite:

```bash
python manage.py test
```

For specific app testing:
```bash
python manage.py test dairy_app
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Mayur Patil**
- GitHub: [@mayur5204](https://github.com/mayur5204)
- 
## 🙏 Acknowledgments

- Django community for the excellent framework
- Bootstrap team for the responsive UI components
- ReportLab for PDF generation capabilities
- All contributors who helped improve this project

## 📞 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/mayur5204/dairy_manager/issues) page
2. Create a new issue with detailed description
3. Contact the maintainer directly

## 🔄 Changelog

### Version 1.0.0
- Initial release with core functionality
- Customer and area management
- Sales and payment tracking
- PDF bill generation
- Multi-language support
- Excel export functionality

---

**Made with ❤️ for the Trimurti Dairy**

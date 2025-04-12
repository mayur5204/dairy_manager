# Dairy Manager

A Django application for managing dairy farm operations.

## Features

- User authentication
- Cattle management
- Milk production tracking
- Financial records
- Reporting and analytics

## Technologies Used

- Django 5.0
- Bootstrap 4
- MySQL (on PythonAnywhere)
- SQLite (local development)

## Deployment

This application is deployed on PythonAnywhere at https://mr0264.pythonanywhere.com/

## Installation

1. Clone the repository
2. Set up virtual environment: `python -m venv venv`
3. Activate virtual environment: `source venv/bin/activate` (Unix) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Run migrations: `python manage.py migrate`
6. Create superuser: `python manage.py createsuperuser`
7. Run server: `python manage.py runserver`

## License

This project is licensed under the MIT License.

"""
Django management command to check PDF generation dependencies
Usage: python manage.py check_pdf_dependencies
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Check if PDF generation dependencies (PyPDF2 and reportlab) are available'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Checking PDF generation dependencies...')
        )

        # Check PyPDF2
        try:
            from PyPDF2 import PdfReader, PdfWriter
            self.stdout.write(
                self.style.SUCCESS('✅ PyPDF2 is available')
            )
            pypdf2_available = True
        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ PyPDF2 is NOT available: {e}')
            )
            pypdf2_available = False

        # Check reportlab
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            self.stdout.write(
                self.style.SUCCESS('✅ reportlab is available')
            )
            reportlab_available = True
        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ reportlab is NOT available: {e}')
            )
            reportlab_available = False

        # Summary
        self.stdout.write('\n' + '='*50)
        if pypdf2_available and reportlab_available:
            self.stdout.write(
                self.style.SUCCESS('✅ All PDF dependencies are available!')
            )
            self.stdout.write('You can generate customer bills without issues.')
        else:
            self.stdout.write(
                self.style.ERROR('❌ Some PDF dependencies are missing!')
            )
            if not pypdf2_available:
                self.stdout.write('To fix PyPDF2: pip install PyPDF2==3.0.1')
            if not reportlab_available:
                self.stdout.write('To fix reportlab: pip install reportlab==4.1.0')

"""
Create a template PDF for bill generation with a second page for day-wise milk table
"""
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors

# Path to save the template
template_dir = os.path.join('dairy_app', 'static', 'pdf_templates')
os.makedirs(template_dir, exist_ok=True)
template_path = os.path.join(template_dir, 'bill_template.pdf')

# Create canvas
c = canvas.Canvas(template_path, pagesize=A4)
width, height = A4

# Define colors
primary_color = colors.HexColor('#4CAF50')  # Green
secondary_color = colors.HexColor('#FFC107')  # Amber

# ========= FIRST PAGE =========
# Add a header
c.setFillColor(primary_color)
c.rect(0, height-3*cm, width, 3*cm, fill=1, stroke=0)

# Add title text
c.setFillColor(colors.white)
c.setFont("Helvetica-Bold", 24)
c.drawString(2*cm, height-2*cm, "Trimurti Dairy")

# Add subtitle
c.setFont("Helvetica-Bold", 16)
c.drawString(2*cm, height-2.8*cm, "Monthly Milk Bill")

# Add customer info section header
c.setFillColor(primary_color)
c.rect(1*cm, height-4*cm, width-2*cm, 0.7*cm, fill=1, stroke=0)

# Add title text for customer section
c.setFillColor(colors.white)
c.setFont("Helvetica-Bold", 12)
c.drawString(1.5*cm, height-3.5*cm, "Customer Information")

# Add a light background box for customer info
c.setFillColor(colors.lightgrey)
c.rect(1*cm, height-8*cm, width-2*cm, 3*cm, fill=1, stroke=0)

# Add table section header
c.setFillColor(primary_color)
c.rect(1*cm, height-9*cm, width-2*cm, 0.7*cm, fill=1, stroke=0)

c.setFillColor(colors.white)
c.setFont("Helvetica-Bold", 12)
c.drawString(1.5*cm, height-8.5*cm, "Milk Delivery Details")

# Add a table outline
c.setFillColor(colors.white)
c.rect(1*cm, height-15*cm, width-2*cm, 5*cm, fill=1, stroke=1)

# Add column headers in the table
c.setFillColor(colors.lightgrey)
c.rect(1*cm, height-10*cm, width-2*cm, 0.8*cm, fill=1, stroke=0)

# Add payment summary header
c.setFillColor(primary_color)
c.rect(1*cm, height-16*cm, width-2*cm, 0.7*cm, fill=1, stroke=0)

c.setFillColor(colors.white)
c.setFont("Helvetica-Bold", 12)
c.drawString(1.5*cm, height-15.5*cm, "Payment Summary")

# Add payment details box
c.setFillColor(colors.lightgrey)
c.rect(1*cm, height-20*cm, width-2*cm, 3*cm, fill=1, stroke=0)

# Add a colored box for final balance
c.setFillColor(secondary_color)
c.rect(width-7*cm, height-21*cm, 5.5*cm, 1.2*cm, fill=1, stroke=0)

# Add a decorative footer
c.setFillColor(primary_color)
c.rect(0, 0, width, 1*cm, fill=1, stroke=0)

# ========= SECOND PAGE - Daily Milk Distribution =========
c.showPage()  # Create a new page

# Add customer and month/year section at the top
c.setFillColor(primary_color)
c.rect(0, height-3*cm, width, 3*cm, fill=1, stroke=0)

# Title for second page
c.setFillColor(colors.white)
c.setFont("Helvetica-Bold", 24)
c.drawString(2*cm, height-2*cm, "Trimurti Dairy")

# Subtitle for second page
c.setFont("Helvetica-Bold", 16)
c.drawString(2*cm, height-2.8*cm, "Daily Milk Distribution")

# Box for customer name and month/year details at the top
c.setFillColor(colors.lightgrey)
c.rect(1*cm, height-4*cm, width-2*cm, 1*cm, fill=1, stroke=0)

# Daily milk distribution table header
c.setFillColor(primary_color)
c.rect(1*cm, height-5.2*cm, width-2*cm, 0.7*cm, fill=1, stroke=0)

c.setFillColor(colors.white)
c.setFont("Helvetica-Bold", 12)
c.drawString(1.5*cm, height-4.7*cm, "Daily Milk Distribution")

# Create a large table area for day-wise milk data
c.setFillColor(colors.white)
c.rect(1*cm, height-22*cm, width-2*cm, 16*cm, fill=1, stroke=1)

# Table column headers
c.setFillColor(colors.lightgrey)
c.rect(1*cm, height-6*cm, width-2*cm, 0.8*cm, fill=1, stroke=0)

# Add a decorative footer on the second page
c.setFillColor(primary_color)
c.rect(0, 0, width, 1*cm, fill=1, stroke=0)

# Add dairy name in the footer
c.setFillColor(colors.white)
c.setFont("Helvetica-Bold", 12)
c.drawString(width/2 - 3*cm, 0.5*cm, "Trimurti Dairy")

c.save()
print(f"Template saved to {template_path}")

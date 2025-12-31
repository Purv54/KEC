from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

import random

import io

def generate_receipt_pdf(order):
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    y = height - 40   # ✅ MUST be int

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(40, y, "KEC Pumps - Payment Receipt")
    y -= 40

    p.setFont("Helvetica", 10)
    p.drawString(40, y, f"Order ID: {order.id}")
    y -= 15
    p.drawString(40, y, f"Name: {order.full_name}")
    y -= 15
    p.drawString(40, y, f"Email: {order.email}")
    y -= 15
    p.drawString(40, y, f"Phone: {order.phone}")
    y -= 15
    p.drawString(40, y, f"Address: {order.address}, {order.city} - {order.pincode}")
    y -= 30

    # Table header
    p.setFont("Helvetica-Bold", 10)
    p.drawString(40, y, "Product")
    p.drawString(260, y, "Qty")
    p.drawString(320, y, "Price")
    p.drawString(400, y, "Total")
    y -= 15

    p.setFont("Helvetica", 10)
    total_amount = 0

    for item in order.items.all():
        line_total = item.price * item.quantity
        total_amount += line_total

        p.drawString(40, y, item.product.name)
        p.drawString(260, y, str(item.quantity))
        p.drawString(320, y, f"₹{item.price}")
        p.drawString(400, y, f"₹{line_total}")
        y -= 15

        if y < 50:
            p.showPage()
            y = height - 40

    y -= 20
    p.setFont("Helvetica-Bold", 11)
    p.drawString(40, y, f"Total Amount Paid: ₹{total_amount}")

    y -= 40
    p.setFont("Helvetica", 9)
    p.drawString(40, y, "Payment Method: Razorpay")
    y -= 15
    p.drawString(40, y, f"Payment ID: {order.razorpay_payment_id}")
    y -= 20
    p.drawString(40, y, "Thank you for shopping with KEC Pumps!")

    p.showPage()
    p.save()

    buffer.seek(0)
    return buffer.getvalue()


def send_order_receipt(order):
    """
    Sends email with PDF receipt attachment
    """

    if not order.email:
        print(f"No email found for Order ID {order.id}. Receipt not sent.")
        return

    # Generate PDF
    pdf_bytes = generate_receipt_pdf(order)

    subject = f"KEC Pumps - Payment Receipt (Order #{order.id})"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [order.email]

    html_content = render_to_string('store/email_receipt.html', {
        'order': order,
        'items': order.items.all(),
        'total': sum(i.price * i.quantity for i in order.items.all())
    })

    text_content = f"""
Thank you for your order!

Order ID: {order.id}
Total Paid: ₹{sum(i.price * i.quantity for i in order.items.all())}

KEC Pumps
"""

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=to_email
    )

    email.attach_alternative(html_content, "text/html")

    # 📎 Attach PDF
    email.attach(
        filename=f"KEC_Receipt_Order_{order.id}.pdf",
        content=pdf_bytes,
        mimetype="application/pdf"
    )

    try:
        email.send()
        print(f"PDF receipt email sent to {order.email}")
    except Exception as e:
        print("Receipt email failed:", e)


def generate_otp():
    return str(random.randint(100000, 999999))
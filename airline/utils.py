import io
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from xhtml2pdf import pisa


def send_ticket_with_pdf(passenger_email, booking_details):

    # ✅ STATUS SAFE
    status = booking_details.get('status', 'Pending').upper()

    # ✅ GET BOOKING OBJECT (VERY IMPORTANT)
    booking = booking_details.get('booking')

    if not booking:
        print("❌ ERROR: Booking object missing")
        return

    # ✅ CONTEXT FOR EMAIL TEMPLATE
    context = {
        'passenger_name': booking_details.get('passenger_name'),
        'flight_no': booking_details.get('flight_no'),

        'airline': booking_details.get('airline'),   # 🔥 ADD THIS
    
        'source': booking_details.get('source'),
        'destination': booking_details.get('destination'),
    
        'date': booking_details.get('date'),              # 🔥 ADD THIS
        'time': booking_details.get('time'),              # 🔥 ADD THIS
        'seat': booking_details.get('seat'),              # 🔥 ADD THIS
    
        'pnr': booking_details.get('pnr'),
        'status': booking_details.get('status'),
    }

    # ✅ SUBJECT + HTML TEMPLATE
    if status == "CANCELLED":
        subject = f"Ticket Cancelled ❌ PNR #{context['pnr']}"
        html_content = render_to_string('emails/cancel_email.html', context)
    else:
        subject = f"Booking Confirmed ✈️ PNR #{context['pnr']}"
        html_content = render_to_string('emails/ticket_email_body.html', context)

    # ✅ TEXT FALLBACK
    text_content = f"""
        Hello {context['passenger_name']},

        Your booking status: {status}
        PNR: {context['pnr']}
        """

    # ✅ CREATE EMAIL OBJECT FIRST
    email = EmailMultiAlternatives(
        subject,
        text_content,
        'Fligo Airlines <sumittripathi8341@gmail.com>',
        [passenger_email],
    )

    email.attach_alternative(html_content, "text/html")

    # ✅ PDF ATTACHMENT (WORKING FIX)
    if status != "CANCELLED":

        try:
            print("🔍 Generating PDF...")

            pdf_html = render_to_string('ticket_pdf.html', {
                'booking': booking   # 🔥 IMPORTANT
            })

            buffer = io.BytesIO()
            pisa_status = pisa.CreatePDF(pdf_html, dest=buffer)

            if not pisa_status.err:
                buffer.seek(0)

                email.attach(
                    f"Ticket_{context['pnr']}.pdf",
                    buffer.read(),
                    'application/pdf'
                )

                print("✅ PDF attached successfully")

            else:
                print("❌ PDF generation failed")

        except Exception as e:
            print("❌ PDF ERROR:", e)

    # ✅ SEND EMAIL
    try:
        email.send(fail_silently=False)
        print("✅ Email sent successfully")
    except Exception as e:
        print("❌ Email send error:", e)
from django.shortcuts import render, redirect
from .models import *
import io
import random
import string
import json
from datetime import date, datetime, timedelta
from django.http import JsonResponse , HttpResponse
from django.contrib import messages
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail , EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from xhtml2pdf import pisa
from .utils import send_ticket_with_pdf
from django.template.loader import get_template
from .models import Reservation
from .models import Flight



# ================= HELPER =================
def generate_pnr():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


# 🔥 MASTER FIX (IMPORTANT)
def update_remaining_seats(flight):
    confirmed = Reservation.objects.filter(
        flight=flight,
        status="Confirmed"
    ).count()

    flight.remaining_seats = flight.total_seats - confirmed
    flight.save()


# ================= HOME =================
def home(request):
    return render(request, "home.html", {
        "today": date.today()
    })


# ================= REGISTER =================
def register(request):

    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # 🔥 CHECK USERNAME
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {
                'error': "Username already exists ❌"
            })

        # 🔥 CHECK EMAIL
        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {
                'error': "Email already registered ❌"
            })

        # ✅ CREATE USER
        User.objects.create(
            username=username,
            email=email,
            password=password
        )

        return redirect('/login')

    return render(request, 'register.html')


# ================= LOGIN =================
from django.contrib.auth.hashers import check_password

def login(request):
    msg = None

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        # 🔥 EXACT MATCH USERNAME (CASE-SENSITIVE)
        user = User.objects.filter(username=username).first()

        if user:
            # ✅ CHECK BOTH (HASHED + OLD PLAIN)
            if check_password(password, user.password) or password == user.password:

                request.session['user'] = user.username

                if 'next' in request.session:
                    next_page = request.session['next']
                    del request.session['next']
                    return redirect(next_page)

                return redirect('/search')

        msg = "Username and Password is Incorrect ❌"

    return render(request, 'login.html', {'msg': msg})


# ================= SEARCH =================
def search(request):

    flights = None
    error = None
    no_flights = None   # ✅ NEW

    if request.method == "POST":

        source = request.POST.get('source')
        destination = request.POST.get('destination')
        travel_date = request.POST.get('travel_date')

        try:
            selected_date = datetime.strptime(travel_date, "%Y-%m-%d").date()
        except:
            selected_date = None

        if not selected_date:
            error = "Please select valid date"

        elif selected_date < date.today():
            error = "You cannot search past dates!"

        else:
            flights = Flight.objects.filter(
                source__icontains=source,
                destination__icontains=destination,
                date=selected_date
            )

            # ✅ CHECK IF NO FLIGHTS
            if not flights.exists():
                no_flights = "No Flights Available ❌"

            else:
                for f in flights:
                    update_remaining_seats(f)

                    if f.remaining_seats <= 0:
                        f.display_seats = "Full"
                        f.is_full = True
                    else:
                        f.display_seats = f.remaining_seats
                        f.is_full = False

    return render(request, 'search.html', {
        'flights': flights,
        'error': error,
        'no_flights': no_flights,   # ✅ PASS TO TEMPLATE
        'today': date.today()
    })

# ================= BOOK =================
def book(request, id):

    if 'user' not in request.session:
        request.session['next'] = request.path
        return redirect('/login')

    flight = Flight.objects.get(id=id)

    travel_date = request.GET.get('date')

    if request.method == "POST":

        seats = request.POST.get("selected_seats")
        travel_date = request.POST.get('travel_date')

        if not seats:
            return render(request, 'book.html', {
                'flight': flight,
                'error': "Select at least one seat",
                'travel_date': travel_date
            })

        return redirect(f"/passenger/{id}/?seats={seats}&date={travel_date}")

    # ✅ FIX: convert queryset → list → JSON
    booked_queryset = Reservation.objects.filter(
        flight=flight,
        status="Confirmed"
    ).values_list('seat_no', flat=True)

    booked_list = list(booked_queryset)

    booked = json.dumps(booked_list)   # 🔥 VERY IMPORTANT

    return render(request, 'book.html', {
        'flight': flight,
        'booked': booked,
        'travel_date': travel_date,
    })



# ================= PASSENGER =================
def passenger(request, id):

    if 'user' not in request.session:
        return redirect('/login')

    flight = Flight.objects.get(id=id)

    seats = request.GET.get('seats')
    travel_date = request.GET.get('date')   # ✅ GET DATE

    if not seats:
        return redirect('/search')

    seats_list = seats.split(",")

    if request.method == "POST":

        booking_data = dict(request.POST)
        booking_data = {k: v[0] if isinstance(v, list) else v for k, v in booking_data.items()}

        booking_data['flight_id'] = id
        booking_data['seats'] = seats
        booking_data['travel_date'] = travel_date   # ✅ STORE DATE

        request.session['booking_data'] = booking_data

        return redirect('/payment')

        # 🔥 CHECK BALANCE
        if wallet.balance < total:
            return HttpResponse("❌ Not enough balance in Fligo wallet")
        
        # 🔥 DEDUCT MONEY
        wallet.balance -= total
        wallet.save()

    return render(request, 'passenger.html', {
        'flight': flight,
        'seats_list': seats_list,
        'travel_date': travel_date   # ✅ SEND TO TEMPLATE
    })


# ================= PAYMENT =================

@transaction.atomic
def payment(request):

    if 'user' not in request.session:
        return redirect('/login')

    user = User.objects.filter(username=request.session['user']).first()
    wallet = Wallet.objects.select_for_update().first()

    data = request.session.get('booking_data')
    if not data:
        return redirect('/search')

    flight = Flight.objects.select_for_update().get(id=data.get('flight_id'))
    total_passengers = int(data.get('total_passengers', 1))
    total = total_passengers * flight.price

    if user:
        print(f"--- DEBUG: User is {user.username}, Email is: '{user.email}' ---")

    # ✅ ONLY RUN PAYMENT LOGIC ON POST
    if request.method == "POST":

        # 🔥 CHECK BALANCE
        if wallet.balance < total:
            messages.error(request, "❌ Payment failed! Not enough balance")
            return redirect('/payment')

        bookings_to_email = []

        # 🔥 CONVERT DATE STRING → DATE OBJECT (FIX)
        travel_date = data.get('travel_date')
        try:
            travel_date = datetime.strptime(travel_date, "%Y-%m-%d").date()
        except:
            travel_date = None

        for i in range(total_passengers):
            name = data.get(f'name_{i}')
            age = data.get(f'age_{i}')
            gender = data.get(f'gender_{i}')
            seat = data.get(f'seat_{i}')

            if not seat or not name:
                continue

            if Reservation.objects.filter(
                flight=flight,
                seat_no=seat,
                status="Confirmed"
            ).exists():
                continue

            status = "Confirmed" if flight.remaining_seats > 0 else "Waiting"

            if status == "Confirmed":
                flight.remaining_seats -= 1

            # ✅ CREATE BOOKING (FIXED DATE)
            new_booking = Reservation.objects.create(
                user=user,
                flight=flight,
                passenger_name=name,
                age=age,
                gender=gender,
                seat_no=seat,
                travel_date=travel_date,   # 🔥 FIXED
                pnr=generate_pnr(),
                status=status
            )

            bookings_to_email.append(new_booking)

        # 🔥 DEDUCT MONEY
        wallet.balance -= total
        wallet.save()

        flight.save()

        # 🔥 SEND EMAILS (FULL FIX)
        for b in bookings_to_email:
            email_data = {
                'passenger_name': b.passenger_name,
                'pnr': b.pnr,
                'flight_no': b.flight.flight_no,

                'airline': b.flight.airline,   # 🔥 ADD THIS

                'source': b.flight.source,
                'destination': b.flight.destination,

                'date': b.travel_date,
                'time': getattr(b.flight, 'departure_time', None),
                'seat': b.seat_no,

                'status': b.status,
                'booking': b   # 🔥 REQUIRED FOR PDF
            }

            try:
                if user and user.email:
                    print("DEBUG EMAIL DATA:", email_data)
                    send_ticket_with_pdf(user.email, email_data)
                    print(f"✅ Email sent to {user.email}")
            except Exception as e:
                print(f"❌ SMTP Error: {e}")

        # 🔥 SUCCESS
        messages.success(request, "✅ Payment successful! Ticket booked ✈️")

        # 🔥 CLEAR SESSION
        if 'booking_data' in request.session:
            del request.session['booking_data']

        return redirect('/mybooking')

    # ✅ GET REQUEST
    return render(request, 'payment.html', {
        'flight': flight,
        'total': total,
        'passengers': total_passengers,
        'wallet': wallet
    })



# ================= MY BOOKING =================
def mybooking(request):
    if 'user' not in request.session:
        request.session['next'] = request.path
        return redirect('/login')

    user = User.objects.filter(username=request.session['user']).first()
    if not user:
        return redirect('/login')

    bookings = Reservation.objects.filter(user=user).order_by('-id')

    # ✅ AUTO EXPIRE LOGIC
    for b in bookings:
        if b.travel_date and b.travel_date < date.today() and b.status == "Confirmed":
            b.status = "Expired"
            b.save()

    return render(request, 'mybooking.html', {
        'bookings': bookings
    })
    
    # ================= CANCEL =================
@transaction.atomic
def cancel(request, id):
    wallet = Wallet.objects.select_for_update().first()
    if 'user' not in request.session:
        return redirect('/login')

    try:
        booking = Reservation.objects.get(
            id=id,
            user__username=request.session['user']
        )
    except Reservation.DoesNotExist:
        return redirect('/mybooking')

    flight = booking.flight

    # ✅ Update status
    booking.status = "Cancelled"
    booking.save()

    # ✅ Promote waiting passenger
    waiting = Reservation.objects.filter(
        flight=flight,
        status="Waiting"
    ).order_by('id').first()

    if waiting:
        waiting.status = "Confirmed"
        waiting.save()

    # ✅ Update seats
    update_remaining_seats(flight)
    
    refund_amount = booking.flight.price
    wallet.balance += refund_amount
    wallet.save()
    # 🔥 SEND CANCELLATION EMAIL
   # 🔥 SEND CANCELLATION EMAIL
    try:
        booking_details = {
            'passenger_name': booking.passenger_name,
            'flight_no': booking.flight.flight_no,
            'source' : booking.flight.source,
            'destination': booking.flight.destination,
            'pnr': booking.pnr,
            'status': "Cancelled",

            'airline': booking.flight.airline,   # 🔥 ADD THIS
    
            'booking': booking   # 🔥 IMPORTANT FIX
        }
    
        send_ticket_with_pdf(
            passenger_email=booking.user.email,
            booking_details=booking_details
        )
    
    except Exception as e:
        print("Email failed ❌", e)

    # ✅ Optional message
    messages.success(request, "Ticket cancelled successfully and email sent ✉️")

    return redirect('/mybooking')

# ================= LOGOUT =================
def logout(request):
    request.session.flush()
    return redirect('/search')


# ================= TICKET =================
def ticket(request, id):

    if 'user' not in request.session:
        return redirect('/login')

    booking = Reservation.objects.get(
        id=id,
        user__username=request.session['user']
    )

    return render(request, 'ticket.html', {'booking': booking})


# ================= CHATBOT =================
@csrf_exempt
def chatbot(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            msg = data.get("message", "").lower().strip()
        except json.JSONDecodeError:
            return JsonResponse({"reply": "Invalid JSON data ❌"})

        # --- FLIGHT SEARCH LOGIC ---
        if "from" in msg and "to" in msg:
            try:
                # Splitting: "flights from Delhi to Mumbai on 2024-12-01"
                parts = msg.split("from")[1].split("to")
                source = parts[0].strip()
                
                rest = parts[1].strip()
                if "on" in rest:
                    destination, date_str = [x.strip() for x in rest.split("on")]
                    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                else:
                    return JsonResponse({"reply": "Please use format: <b>from Source to Destination on YYYY-MM-DD</b><br><br>"})

                flights = Flight.objects.filter(
                    source__icontains=source,
                    destination__icontains=destination,
                    date=selected_date
                )

                if not flights.exists():
                    reply = f"✈ No flights found from {source} to {destination} on {date_str} ❌<br><br>"
                else:
                    reply = "<b>Available Flights:</b><br><hr>"
                    for f in flights:
                        # Ensure this function exists in your utils or models
                        # update_remaining_seats(f) 

                        status_color = "#28a745" if f.remaining_seats > 0 else "#ffc107"
                        btn_text = "Book Now" if f.remaining_seats > 0 else "Join Waitlist"
                        
                        reply += f"""
                        ✈ <b>{f.flight_no}</b> ({f.source} → {f.destination})<br>
                        Price: ₹{f.price} | Seats: {f.remaining_seats}<br>
                        <a href="/book/{f.id}/?date={f.date}" 
                           style="background:{status_color};color:white;padding:3px 8px;text-decoration:none;border-radius:4px;display:inline-block;">
                           {btn_text}
                        </a><hr>
                        """
            except Exception as e:
                reply = "Search failed. Use: <b>from Source to Destination on YYYY-MM-DD</b><br><br>"

        # --- PNR STATUS LOGIC ---
        elif "pnr" in msg or "check" in msg:
            try:
                # Extracting PNR: removes "check" and "pnr" and leaves the code
                pnr = msg.replace("check", "").replace("pnr", "").strip().upper()
                
                booking = Reservation.objects.get(pnr=pnr)
                reply = f"""
                <b>Ticket Found!</b><br>
                Passenger: {booking.passenger_name}<br>
                Flight: {booking.flight.flight_no}<br>
                Status: <b>{booking.status}</b><br>
                Seat: {booking.seat_no}
                <br><br>
                """
            except Reservation.DoesNotExist:
                reply = "PNR not found ❌ Please check the number.<br><br>"
            except Exception:
                reply = "Please provide a valid PNR number."

        # --- DEFAULT RESPONSE ---
        else:
            reply = """Hello! I am your Flight AI. 🤖<br>
            Try asking:<br>
            1️⃣ <i>"flights from Delhi to Mumbai on 2024-05-20"</i><br>
            2️⃣ <i>"check pnr ABC123"</i><br><br>"""
            

        return JsonResponse({"reply": reply})

    return JsonResponse({"error": "Only POST allowed"}, status=405)


def terms(request):
    return render(request, 'terms.html')





def download_ticket(request, id):
    booking = Reservation.objects.get(id=id)

    template = get_template('ticket_pdf.html')
    html = template.render({'booking': booking})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Ticket_{booking.pnr}.pdf"'

    pisa.CreatePDF(html, dest=response)

    return response


def airline_flights(request, airline):

    today = date.today()

    # 🔥 FILTER FUTURE FLIGHTS ONLY
    flights = Flight.objects.filter(
        airline__iexact=airline,
        date__gte=today
    ).order_by('date', 'departure_time')

    # 🟢 ADD LABELS (Today / Tomorrow)
    for f in flights:
        if f.date == today:
            f.day_label = "Today"
        elif f.date == today + timedelta(days=1):
            f.day_label = "Tomorrow"
        else:
            f.day_label = f.date.strftime("%d %b %Y")

    return render(request, 'airline_flights.html', {
        'flights': flights,
        'airline': airline,
        'today': today
    })



# def route_flights(request, city):
#     flights = Flight.objects.filter(source__iexact=city).order_by('date')
#     # get unique dates
#     dates = flights.values_list('date', flat=True).distinct()
#     return render(request, 'route_flights.html', {
#         'flights': flights,
#         'city': city,
#         'date': date
#     })
def route_flights(request, city):

    # 🔥 FILTER ONLY TODAY + FUTURE FLIGHTS
    flights = Flight.objects.filter(
        source__iexact=city,
        date__gte=date.today()   # ✅ FIX
    ).order_by('date')

    return render(request, 'route_flights.html', {
        'flights': flights,
        'city': city,
        'today': date.today()   # (optional)
    })


import random
from django.core.mail import send_mail

# ================= FORGOT PASSWORD =================
def forgot_password(request):

    if request.method == "POST":
        username = request.POST.get("username")

        user = User.objects.filter(username=username).first()

        if not user:
            return render(request, "forgot_password.html", {"error": "User not found ❌"})

        # 🔥 GENERATE OTP
        otp = str(random.randint(100000, 999999))

        # SAVE IN SESSION
        request.session['reset_username'] = username
        request.session['otp'] = otp

        # SEND EMAIL
        send_mail(
            "Fligo OTP Verification 🔐",
            f"Your OTP is: {otp}",
            "sumittripathi8341@gmail.com",
            [user.email],
            fail_silently=False,
        )

        return redirect('/verify-otp/')

    return render(request, "forgot_password.html")


def verify_otp(request):

    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        real_otp = request.session.get("otp")

        if entered_otp == real_otp:
            return redirect('/reset-password/')
        else:
            return render(request, "verify_otp.html", {"error": "Invalid OTP ❌"})

    return render(request, "verify_otp.html")


def reset_password(request):

    username = request.session.get("reset_username")

    if not username:
        return redirect('/login')

    user = User.objects.filter(username=username).first()

    if request.method == "POST":
        new_password = request.POST.get("password")

        user.password = new_password
        user.save()

        # CLEAR SESSION
        request.session.pop("otp", None)
        request.session.pop("reset_username", None)

        return redirect('/login')

    return render(request, "reset_password.html")



def clear_bookings(request):

    if 'user' not in request.session:
        return redirect('/login')

    user = User.objects.filter(username=request.session['user']).first()

    if request.method == "POST":
        Reservation.objects.filter(
            user=user,
            status__in=["Cancelled", "Expired"]
        ).delete()

    return redirect('/mybooking')
from django.db import models
from django.contrib.auth.models import User

# ✈️ Flight Model
class Flight(models.Model):

    flight_no = models.CharField(max_length=20)
    airline = models.CharField(max_length=100)

    source = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)

    departure_time = models.CharField(max_length=50)
    arrival_time = models.CharField(max_length=50)

    date = models.DateField()

    total_seats = models.IntegerField()
    remaining_seats = models.IntegerField()

    price = models.IntegerField()

    def __str__(self):
        return f"{self.flight_no} ({self.date})"


# 🎟 Reservation Model
class Reservation(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)  # ✅ Django User
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE)

    passenger_name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10)
    seat_no = models.CharField(max_length=10)

    booking_date = models.DateField(auto_now_add=True)
    travel_date = models.DateField(null=True, blank=True)

    pnr = models.CharField(max_length=20, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, default="Confirmed")

    def __str__(self):
        return f"{self.user.username} - {self.flight.flight_no}"


# 💳 Wallet Model
class Wallet(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, default="Fligo")
    balance = models.FloatField(default=0)

    def __str__(self):
        return f"{self.user.username} - ₹{self.balance}"
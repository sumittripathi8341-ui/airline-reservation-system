from django.db import models

# Create your models here.

class User(models.Model):
    username = models.CharField(max_length=50)
    email = models.CharField(max_length=100)
    password = models.CharField(max_length=50)

    def __str__(self):
        return self.username


from django.db import models

class Flight(models.Model):

    flight_no = models.CharField(max_length=20)
    airline = models.CharField(max_length=100)

    source = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)

    departure_time = models.CharField(max_length=50)
    arrival_time = models.CharField(max_length=50)

    date = models.DateField()   # ✅ NEW FIELD

    total_seats = models.IntegerField()
    remaining_seats = models.IntegerField()

    price = models.IntegerField()

    def __str__(self):
        return f"{self.flight_no} ({self.date})"


class Reservation(models.Model):

    user = models.ForeignKey(User,on_delete=models.CASCADE)
    flight = models.ForeignKey(Flight,on_delete=models.CASCADE)

    passenger_name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10)
    seat_no = models.CharField(max_length=10)

    booking_date = models.DateField(auto_now_add=True)
    travel_date = models.DateField(null=True, blank=True)
    pnr = models.CharField(max_length=20, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, default="Confirmed")


from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Reservation

@receiver(post_delete, sender=Reservation)
def increase_seat_on_delete(sender, instance, **kwargs):

    flight = instance.flight

    flight.remaining_seats += 1
    flight.save()

class Wallet(models.Model):
    name = models.CharField(max_length=50, default="Fligo")
    balance = models.FloatField(default=10000000)  # 10 lakh = 1000000, 100 lakh = 1 crore

    def __str__(self):
        return f"{self.name} - ₹{self.balance}"    
from django.contrib import admin
from .models import User, Flight, Reservation

# Register your models here.
admin.site.register(User)
admin.site.register(Flight)
admin.site.register(Reservation)
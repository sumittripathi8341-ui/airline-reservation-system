from django.urls import path
from . import views
from django.views.generic import TemplateView

urlpatterns = [

    path('', views.home, name='home'),

    path('register/', views.register, name='register'),

    path('login/', views.login, name='login'),

    path('search/', views.search, name='search'),

    path('book/<int:id>/', views.book, name='book'),

    path('mybooking/', views.mybooking, name='mybooking'),

    path('cancel/<int:id>/', views.cancel, name='cancel'),

    path('logout/', views.logout, name='logout'),
    path('ticket/<int:id>/', views.ticket),

    path('chatbot/', views.chatbot),

    path('passenger/<int:id>/', views.passenger),
    path('payment/', views.payment),
    path('terms/', views.terms, name='terms'),


    path('download-ticket/<int:id>/', views.download_ticket),
    path('airline/<str:airline>/', views.airline_flights, name='airline_flights'),
    path('routes/<str:city>/', views.route_flights, name='route_flights'),

    path('terms/', TemplateView.as_view(template_name='terms.html')),
    path('privacy/', TemplateView.as_view(template_name='privacy.html')),
    path('refund/', TemplateView.as_view(template_name='refund.html')),

    path('forgot-password/', views.forgot_password),
    path('verify-otp/', views.verify_otp),
    path('reset-password/', views.reset_password),

    path('clear-bookings/', views.clear_bookings),
    path('fake-upi-pay/', views.fake_upi_pay, name='fake_upi_pay'),


]
"""
URL configuration for christ project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from tours import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', views.home, name='home'),
    path('tours/', views.tour_list, name='tour_list'),
    path('tours/<slug:slug>/', views.tour_detail, name='tour_detail'),
    path('tours/<slug:slug>/book/', views.book_tour, name='book_tour'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('booking/<int:inquiry_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('api/initiate-mpesa-payment/', views.initiate_mpesa_payment, name='initiate_mpesa_payment'),
    path('api/payment-status/<int:inquiry_id>/', views.check_payment_status, name='check_payment_status'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    # Manager Views
    path('manager/', views.manager_overview, name='manager_dashboard'),
    path('manager/tours/', views.manager_tours, name='manager_tours'),
    path('manager/clients/', views.manager_clients, name='manager_clients'),
    path('manager/bookings/', views.manager_bookings, name='manager_bookings'),
    
    # Tour Actions
    path('manager/tour/add/', views.manager_tour_create, name='manager_tour_create'),
    path('manager/tour/<slug:slug>/edit/', views.manager_tour_edit, name='manager_tour_edit'),
    path('manager/tour/<slug:slug>/delete/', views.manager_tour_delete, name='manager_tour_delete'),
    path('manager/booking/<int:inquiry_id>/status/<str:status>/', views.update_booking_status, name='update_booking_status'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('booking-success/', views.booking_success, name='booking_success'),
    path('api/pay-balance/', views.pay_balance, name='pay_balance'),
    path('legal/privacy/', views.privacy_policy, name='privacy'),
    path('legal/terms/', views.terms_of_service, name='terms'),
    path('legal/cancellation/', views.cancellation_policy, name='cancellation'),
    path('legal/cookies/', views.cookie_policy, name='cookies'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

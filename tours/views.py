from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import Tour, Inquiry, UserProfile
from .forms import InquiryForm
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib import messages
from datetime import date, timedelta
from django_daraja.mpesa.core import MpesaClient
import json


def home(request):
    # Get the 3 most recently added tours that are published
    featured_tours = Tour.objects.filter(is_published=True).order_by('-id')[:3]
    return render(request, 'home.html', {'featured_tours': featured_tours})


def tour_list(request):
    # Fetch all published tours from the database
    tours = Tour.objects.filter(is_published=True).order_by('start_date')
    return render(request, 'tours.html', {'tours': tours})


def tour_detail(request, slug):
    # Find the tour by its slug, or return a 404 error if it doesn't exist
    tour = get_object_or_404(Tour, slug=slug, is_published=True)

    # 1. Fetch the actual Inquiry object, not just a boolean
    user_inquiry = None
    if request.user.is_authenticated:
        user_inquiry = Inquiry.objects.filter(
            user=request.user,
            tour=tour,
            is_cancelled=False
        ).first()

    # CHECK IF EVENT IS IN THE PAST
    is_past = False
    if tour.start_date and tour.start_date < date.today():
        is_past = True

    return render(request, 'tour_detail.html', {
        'tour': tour,
        'user_inquiry': user_inquiry,
        'is_past': is_past,
    })


@login_required
def book_tour(request, slug):
    if not request.user.is_authenticated:
        return redirect(f'/tours/{slug}/?login_required=true')
        
    tour = get_object_or_404(Tour, slug=slug, is_published=True)
    
    # --- NEW: BLOCK PAST EVENTS IN BACKEND ---
    if tour.start_date and tour.start_date < date.today():
        messages.error(request, "This tour has already passed and can no longer be booked.")
        return redirect('tour_detail', slug=slug)
    # -----------------------------------------

    # 1. Check for double booking
    if Inquiry.objects.filter(user=request.user, tour=tour, is_cancelled=False).exists():
        return redirect(f'/tours/{slug}/?already_booked=true')

    # 2. Check if they have a phone number
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if not profile.phone:
        messages.warning(request, "You must add a phone number to your profile before you can book a tour.")
        return redirect('/profile/#settings')

    if request.method == 'POST':
        # We only need the group size from the POST request
        group_size = int(request.POST.get('group_size', 1))
        if group_size < 1:
            group_size = 1
        
        if tour.slots_available is not None and tour.slots_available < group_size:
            messages.error(request, f"Sorry, only {tour.slots_available} slots are available for this tour.")
            return redirect('tour_detail', slug=slug)
            
        # Create the booking automatically
        inquiry = Inquiry.objects.create(
            user=request.user,
            tour=tour,
            name=request.user.get_full_name() or request.user.username,
            email=request.user.email,
            phone=profile.phone,
            group_size=group_size,
            status='new'
        )
        
        # --- PAYMENT MATH ---
        price_per_person = tour.price_from if tour.price_from else 0
        inquiry.total_price = price_per_person * group_size
        if inquiry.total_price > 0:
            inquiry.deposit_paid = round(float(inquiry.total_price) * 0.20, 2)
            inquiry.balance_due = round(float(inquiry.total_price) - float(inquiry.deposit_paid), 2)
        else:
            inquiry.deposit_paid = 0
            inquiry.balance_due = 0
            
        if tour.start_date:
            inquiry.final_payment_due_date = tour.start_date - timedelta(days=2)
            
        inquiry.save()
        
        # Reduce slots
        if tour.slots_available is not None and tour.slots_available >= group_size:
            tour.slots_available -= group_size
            tour.save()
            
        # --- EMAIL ENGINE ---
        try:
            send_mail(
                f"NEW BOOKING: {inquiry.name} - {tour.title}",
                f"User: {inquiry.name}\nPhone: {inquiry.phone}\nGroup Size: {inquiry.group_size}\nTotal: KSh {inquiry.total_price}\nDeposit Due: KSh {inquiry.deposit_paid}",
                settings.DEFAULT_FROM_EMAIL,
                [settings.EMAIL_HOST_USER],
                fail_silently=False,
            )
            send_mail(
                f"Booking Received: {tour.title}",
                f"Dear {inquiry.name},\n\nThank you for booking {tour.title}. We have received your request.\n\nTotal: KSh {inquiry.total_price}\nDeposit Required (20%): KSh {inquiry.deposit_paid}\nBalance Due: KSh {inquiry.balance_due}\n\nBlessings,\nThe CCA Team",
                settings.DEFAULT_FROM_EMAIL,
                [inquiry.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Email failed: {e}")
            
        return render(request, 'booking_success.html', {'tour': tour, 'inquiry': inquiry})
    
    # If it's a GET request, show the 1-step checkout page
    return render(request, 'book_tour.html', {'tour': tour, 'profile': profile})


# --- CLIENT ACCOUNTS ---

class SignUpView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'


@login_required
def profile(request):
    # Ensure profile exists
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    # Get active bookings
    my_inquiries = Inquiry.objects.filter(user=request.user, is_cancelled=False).order_by('tour__start_date')

    # Get past/cancelled bookings
    cancelled_inquiries = Inquiry.objects.filter(user=request.user, is_cancelled=True).order_by('-submitted_at')

    return render(request, 'profile.html', {
        'profile': profile,
        'inquiries': my_inquiries,
        'cancelled_inquiries': cancelled_inquiries
    })


@login_required
def update_profile(request):
    if request.method == 'POST':
        # Update User fields
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()

        # Update Profile fields
        profile = request.user.userprofile
        profile.phone = request.POST.get('phone', '')
        profile.location = request.POST.get('location', '')
        profile.passport_number = request.POST.get('passport_number', '')
        profile.emergency_contact = request.POST.get('emergency_contact', '')
        profile.dietary_restrictions = request.POST.get('dietary_restrictions', '')
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        profile.save()

        return redirect('profile')
    return redirect('profile')


@login_required
def cancel_booking(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id, user=request.user)

    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided')
        inquiry.is_cancelled = True
        inquiry.cancellation_reason = reason
        inquiry.status = 'cancelled'
        inquiry.save()

    return redirect('profile')


def success(request):
    return render(request, 'success.html')


# --- MANAGER DASHBOARD ---

@login_required
def manager_overview(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    
    bookings = Inquiry.objects.all().order_by('-submitted_at')
    context = {
        'total_bookings': bookings.filter(is_cancelled=False).count(),
        'pending_bookings': bookings.filter(status='new', is_cancelled=False).count(),
        'total_tours': Tour.objects.filter(is_published=True).count(),
        'recent_bookings': bookings[:5],
    }
    return render(request, 'manager/overview.html', context)


@login_required
def manager_tours(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    all_tours = Tour.objects.all().order_by('-id')
    return render(request, 'manager/tours.html', {'all_tours': all_tours})


@login_required
def manager_bookings(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    all_bookings = Inquiry.objects.all().order_by('-submitted_at')
    return render(request, 'manager/bookings.html', {'bookings': all_bookings})


from .forms import TourForm


# --- MANAGER TOUR MANAGEMENT ---

@login_required
def manager_tour_create(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access Denied")
    
    if request.method == 'POST':
        form = TourForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('manager_dashboard')
    else:
        form = TourForm()
    
    return render(request, 'manager_tour_form.html', {'form': form, 'action': 'Add New Tour'})


@login_required
def manager_tour_edit(request, slug):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access Denied")
    
    tour = get_object_or_404(Tour, slug=slug)
    
    if request.method == 'POST':
        form = TourForm(request.POST, request.FILES, instance=tour)
        if form.is_valid():
            form.save()
            return redirect('manager_dashboard')
    else:
        form = TourForm(instance=tour)
    
    return render(request, 'manager_tour_form.html', {'form': form, 'action': 'Edit Tour', 'tour': tour})


@login_required
def manager_tour_delete(request, slug):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access Denied")
    
    tour = get_object_or_404(Tour, slug=slug)
    if request.method == 'POST':
        tour.delete()
        return redirect('manager_dashboard')
    
    return redirect('manager_dashboard')


from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required


@login_required
def update_booking_status(request, inquiry_id, status):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access Denied")

    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    inquiry.status = status
    inquiry.save()
    return redirect('manager_dashboard')


@login_required
def manager_clients(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    # Get all users who are NOT admins/staff
    clients = User.objects.filter(is_superuser=False, is_staff=False).order_by('-date_joined')

    return render(request, 'manager/clients.html', {'clients': clients})


# --- STATIC SUB-PAGES ---


def about(request):
    return render(request, 'about.html')


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message_body = request.POST.get('message')

        try:
            send_mail(
                f"Website Contact: {subject}",
                f"From: {name} ({email})\n\nMessage:\n{message_body}",
                settings.DEFAULT_FROM_EMAIL,
                [settings.EMAIL_HOST_USER],
                fail_silently=False,
            )
            messages.success(request, "Your message has been sent successfully. We will get back to you soon!")
        except Exception:
            messages.error(request, "Sorry, there was an error sending your message. Please try again later.")

        return redirect('contact')

    return render(request, 'contact.html')


def privacy_policy(request):
    return render(request, 'legal/privacy.html')


def terms_of_service(request):
    return render(request, 'legal/terms.html')


def cancellation_policy(request):
    return render(request, 'legal/cancellation.html')


def cookie_policy(request):
    return render(request, 'legal/cookies.html')


@csrf_exempt
def initiate_mpesa_payment(request):
    if request.method == 'POST':
        try:
            # 1. Get data from the form
            phone_number = request.POST.get('phone_number')
            amount = int(float(request.POST.get('amount')))
            group_size = int(request.POST.get('group_size', 1))
            tour_slug = request.POST.get('tour_slug')

            # Format phone number
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            elif phone_number.startswith('+'):
                phone_number = phone_number[1:]

            if not phone_number or not amount or not tour_slug:
                return JsonResponse({'success': False, 'message': 'Missing required details.'})

            # 2. Create the Inquiry (Booking) in the database
            tour = get_object_or_404(Tour, slug=tour_slug)

            # --- DOUBLE BOOKING CHECK ---
            if Inquiry.objects.filter(user=request.user, tour=tour, is_cancelled=False).exists():
                return JsonResponse({'success': False, 'message': 'You have already booked this tour.'})

            inquiry = Inquiry.objects.create(
                user=request.user,
                tour=tour,
                name=request.user.get_full_name() or request.user.username,
                email=request.user.email,
                phone=phone_number,
                group_size=group_size,
                status='pending'
            )

            # Calculate prices
            inquiry.total_price = tour.price_from * group_size
            inquiry.deposit_paid = float(amount)
            inquiry.balance_due = float(inquiry.total_price) - float(inquiry.deposit_paid)
            inquiry.save()

            # 3. Initiate the STK Push
            cl = MpesaClient()
            ngrok_url = "https://lustrous-smooth-platinum.ngrok-free.dev"
            callback_url = f'{ngrok_url}/mpesa/callback/'

            account_reference = f'CCA-Booking-{inquiry.id}'
            transaction_desc = 'Christ Centered Adventures Deposit'

            response = cl.stk_push(phone_number, amount, account_reference, transaction_desc, callback_url)

            # Save the CheckoutRequestID so we can match the callback later
            if hasattr(response, 'checkout_request_id') and response.checkout_request_id:
                inquiry.checkout_request_id = response.checkout_request_id
                inquiry.save()

            return JsonResponse({
                'success': True,
                'message': 'STK Push sent. Please check your phone to enter your M-Pesa PIN.',
                'inquiry_id': inquiry.id,
            })
        except Exception as e:
            print(f"🚨 MPESA PAYMENT ERROR: {e}")
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@csrf_exempt
def mpesa_callback(request):
    if request.method == 'POST':
        try:
            callback_data = json.loads(request.body)
            stk_callback = callback_data.get('Body', {}).get('stkCallback', {})

            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')
            checkout_request_id = stk_callback.get('CheckoutRequestID')

            # Find the booking using the CheckoutRequestID
            inquiry = Inquiry.objects.filter(checkout_request_id=checkout_request_id).first()

            if not inquiry:
                print(f"❌ Callback Error: Booking not found for CheckoutID {checkout_request_id}")
                return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Booking not found.'})

            if result_code == 0:
                # PAYMENT SUCCESSFUL

                # Distinguish balance vs deposit payment by reference
                if inquiry.deposit_paid > 0 and inquiry.balance_due > 0:
                    # This is a BALANCE payment
                    inquiry.balance_due = 0
                    inquiry.is_fully_paid = True
                    inquiry.status = 'booked'
                    inquiry.save()
                    print(f"✅ Balance payment successful for Booking {inquiry.id}")
                else:
                    # This is a DEPOSIT payment
                    inquiry.status = 'booked'
                    inquiry.save()

                    tour = inquiry.tour
                    if tour.slots_available >= inquiry.group_size:
                        tour.slots_available -= inquiry.group_size
                        tour.save()

                    print(f"✅ Deposit payment successful for Booking {inquiry.id}")

            else:
                # PAYMENT FAILED OR CANCELLED
                inquiry.status = 'cancelled'
                inquiry.is_cancelled = True
                inquiry.cancellation_reason = f"Payment failed: {result_desc}"
                inquiry.save()

                print(f"❌ Payment failed for Booking {inquiry.id}: {result_desc}")

            return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Callback received successfully.'})
        except Exception as e:
            print(f"Callback Error: {e}")
            return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Callback processing failed.'})

    return JsonResponse({'ResultCode': 1, 'ResultDesc': 'Invalid request method.'})


@login_required
def check_payment_status(request, inquiry_id):
    try:
        inquiry = Inquiry.objects.get(id=inquiry_id, user=request.user)
        return JsonResponse({'status': inquiry.status})
    except Inquiry.DoesNotExist:
        return JsonResponse({'status': 'not_found'})


@login_required
def booking_success(request):
    return render(request, 'booking_success.html')


@csrf_exempt
@login_required
def pay_balance(request):
    if request.method == 'POST':
        try:
            amount = int(float(request.POST.get('amount')))
            inquiry_id = request.POST.get('inquiry_id')

            inquiry = get_object_or_404(Inquiry, id=inquiry_id, user=request.user)

            # Get the phone number from the database instead of the form
            phone_number = inquiry.phone

            if not phone_number:
                return JsonResponse({'success': False, 'message': 'No phone number on file. Please contact support.'})

            if inquiry.balance_due <= 0:
                return JsonResponse({'success': False, 'message': 'You have no balance to pay.'})

            cl = MpesaClient()
            ngrok_url = "https://lustrous-smooth-platinum.ngrok-free.dev" # YOUR NGROK URL
            callback_url = f'{ngrok_url}/mpesa/callback/'
            
            account_reference = f'CCA-Balance-{inquiry.id}'
            transaction_desc = 'CCA Final Balance Payment'

            response = cl.stk_push(phone_number, amount, account_reference, transaction_desc, callback_url)

            if response.checkout_request_id:
                inquiry.checkout_request_id = response.checkout_request_id
                inquiry.save()

            return JsonResponse({'success': True, 'message': 'STK Push sent to your saved number.'})
        except Exception as e:
            print(f"🚨 BALANCE PAYMENT ERROR: {e}")
            return JsonResponse({'success': False, 'message': str(e)})
            
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})
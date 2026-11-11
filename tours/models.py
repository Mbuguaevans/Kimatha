from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Tour(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, help_text="URL-friendly version of the title (e.g. holy-land-pilgrimage)")
    summary = models.TextField(blank=True)
    description = models.TextField(blank=True)
    destination = models.CharField(max_length=200, blank=True)
    duration_days = models.IntegerField(default=1)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    price_from = models.IntegerField(null=True, blank=True, help_text="Price in USD")
    slots_available = models.IntegerField(default=10, help_text="Number of available spots")
    hero_image = models.ImageField(upload_to='tours/', null=True, blank=True)
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Inquiry(models.Model):
    GROUP_TYPES = [
        ('individual', 'Individual'),
        ('family', 'Family'),
        ('church_group', 'Church Group'),
        ('retreat_planner', 'Retreat Organizer'),
    ]
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('booked', 'Booked'),
        ('closed', 'Closed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    group_type = models.CharField(max_length=50, choices=GROUP_TYPES, default='individual')
    group_size = models.IntegerField(null=True, blank=True)
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, null=True, blank=True, related_name='inquiries')
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True, null=True)
    
    # --- NEW PAYMENT FIELDS ---
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deposit_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_payment_due_date = models.DateField(null=True, blank=True)
    is_fully_paid = models.BooleanField(default=False)
    checkout_request_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Inquiries"

    def __str__(self):
        return f"{self.name} - {self.tour.title if self.tour else 'General Inquiry'}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=100, blank=True, help_text="City, Country")
    passport_number = models.CharField(max_length=50, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    dietary_restrictions = models.TextField(blank=True, help_text="Allergies, medical needs, etc.")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, help_text="Profile Picture")

    def __str__(self):
        return f"{self.user.username}'s Profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

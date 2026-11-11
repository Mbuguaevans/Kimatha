from django.contrib import admin
from .models import Tour, Inquiry

@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = ('title', 'destination', 'start_date', 'price_from', 'slots_available', 'is_published')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'tour', 'status', 'submitted_at')
    list_filter = ('status', 'group_type')
    search_fields = ('name', 'email', 'message')

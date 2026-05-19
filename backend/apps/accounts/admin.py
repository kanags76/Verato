from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Invitation, Organisation, Person, User


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display  = ['name', 'slug', 'created_at']
    search_fields = ['name', 'slug']


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ['username', 'email', 'organisation', 'is_staff']
    list_filter   = ['organisation', 'is_staff']
    fieldsets     = UserAdmin.fieldsets + (
        ('Organisation', {'fields': ('organisation',)}),
    )


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display  = ['name', 'organisation', 'meeting_count', 'delivery_rate', 'first_seen_at']
    list_filter   = ['organisation']
    search_fields = ['name', 'email']


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display  = ['email', 'organisation', 'invited_by', 'accepted_at', 'expires_at', 'created_at']
    list_filter   = ['organisation']
    search_fields = ['email']
    readonly_fields = ['token', 'created_at']

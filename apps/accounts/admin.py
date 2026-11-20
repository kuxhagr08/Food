from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Address

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'phone', 'is_online', 'is_active')
    list_filter = ('role', 'is_online', 'is_active', 'is_staff')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Role & Status', {'fields': ('role', 'is_online', 'current_lat', 'current_lng', 'last_location_updated_at')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'role', 'first_name', 'last_name', 'password'),
        }),
    )
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    ordering = ('-created_at',)

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'address_line1', 'city', 'pincode', 'is_default')
    list_filter = ('city', 'is_default')
    search_fields = ('user__email', 'address_line1', 'city', 'pincode')


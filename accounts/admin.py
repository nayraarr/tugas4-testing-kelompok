import django
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from accounts.models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'email', 'role', 'is_active']
    list_filter = ['role', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Info Tambahan', {'fields': ('role', 'no_telp', 'alamat', 'tanggal_lahir')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Info Tambahan', {'fields': ('role', 'first_name', 'last_name', 'email', 'no_telp')}),
    )

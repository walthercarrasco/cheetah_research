from django.contrib import admin
from .models import User
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'is_staff')
    list_filter = ('is_active', 'is_staff')
    actions = ['approve_users']

    def approve_users(self, request, queryset):
        queryset.update(is_active=True)

admin.site.register(User, UserAdmin)
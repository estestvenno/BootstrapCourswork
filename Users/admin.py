from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile

from django.utils.html import format_html


# INLINE для отображения профиля внутри пользователя
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль'
    readonly_fields = ('avatar_tag',)

    def avatar_tag(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="80" height="80" style="border-radius: 50%; object-fit: cover;" />',
                               obj.avatar.url)
        return "-"

    avatar_tag.short_description = 'Аватар'


# Расширяем стандартный UserAdmin
class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'is_staff', 'profile_avatar')

    def profile_avatar(self, obj):
        try:
            avatar = obj.profile.avatar.url
            return format_html('<img src="{}" width="30" height="30" style="border-radius: 50%; object-fit: cover;" />',
                               avatar)
        except (Profile.DoesNotExist, AttributeError):
            return "–"

    profile_avatar.short_description = 'Аватар'

    actions_on_top = True
    actions_on_bottom = False


# Перерегистрируем User
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

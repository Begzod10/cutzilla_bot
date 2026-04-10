from django.contrib import admin
from .models import Users
from django import forms


class UsersAdminForm(forms.ModelForm):
    # write-only field; won’t show the hash
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        help_text="Leave blank to keep the current password."
    )

    class Meta:
        model = Users
        # include all fields you want editable in admin + this write-only password
        fields = ("first_name", "last_name", "role", "username", "telegram_id", "password")

    def save(self, commit=True):
        user = super().save(commit=False)
        raw = self.cleaned_data.get("password")
        if raw:  # only when provided
            user.set_password(raw)  # hashes correctly
        if commit:
            user.save()
        return user


class UsersAdmin(admin.ModelAdmin):
    form = UsersAdminForm
    list_display = ("first_name", "last_name", "role", "telegram_id")


admin.site.register(Users, UsersAdmin)

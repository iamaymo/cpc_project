from django import forms
from django.contrib import admin
from .models import Users


class UsersAdminForm(forms.ModelForm):
    password = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(render_value=False),
        required=False,
        help_text="أدخل كلمة المرور للمستخدم (سيتم تشفيرها تلقائياً)."
    )

    class Meta:
        model = Users
        fields = '__all__'


@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    form = UsersAdminForm
    list_display = ('full_name', 'phone_number', 'username', 'role', 'add_at')
    list_filter = ('role', 'add_at')
    search_fields = ('full_name', 'phone_number', 'username')
    readonly_fields = ('username', 'add_at')
    fields = ('full_name', 'phone_number', 'password', 'role', 'username', 'add_at')

    def save_model(self, request, obj, form, change):
        # Auto-set username to match phone_number
        obj.username = obj.phone_number

        # If a new password was provided in the form
        new_password = form.cleaned_data.get('password')
        if new_password:
            obj.set_password(new_password)
        elif not change and not obj.password:
            # For new record without password, keep empty or handle
            pass

        super().save_model(request, obj, form, change)

from django import forms
from django.db.models import Q
from .models import Users


def normalize_phone_number(phone_str):
    if not phone_str:
        return ''
    arabic_numerals = {
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }
    for ar, en in arabic_numerals.items():
        phone_str = phone_str.replace(ar, en)
    return ''.join(c for c in phone_str.strip() if c.isdigit() or c == '+')


class LoginForm(forms.Form):
    phone_number = forms.CharField(
        max_length=20,
        label='رقم الهاتف',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
            'placeholder': 'أدخل رقم الهاتف (مثال: 7XXXXXXXX)',
            'autocomplete': 'tel',
            'dir': 'ltr',
        }),
        error_messages={
            'required': 'يرجى إدخال رقم الهاتف.',
        }
    )

    password = forms.CharField(
        label='كلمة المرور',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
            'placeholder': 'أدخل كلمة المرور',
            'autocomplete': 'current-password',
        }),
        error_messages={
            'required': 'يرجى إدخال كلمة المرور.',
        }
    )

    def clean(self):
        cleaned_data = super().clean()
        phone_input = cleaned_data.get('phone_number')
        password = cleaned_data.get('password')

        if not phone_input or not password:
            return cleaned_data

        cleaned_phone = normalize_phone_number(phone_input)
        raw_phone = phone_input.strip()

        # Find user in Users model by phone_number or username
        account = Users.objects.filter(
            Q(phone_number=cleaned_phone) |
            Q(username=cleaned_phone) |
            Q(phone_number=raw_phone) |
            Q(username=raw_phone)
        ).first()

        if not account:
            self.add_error(
                'phone_number',
                'لا يوجد حساب مسجل برقم الهاتف المدخل.'
            )
            return cleaned_data

        if not account.check_password(password):
            self.add_error(
                'password',
                'كلمة المرور غير صحيحة، يرجى المحاولة مجدداً.'
            )
            return cleaned_data

        self.account = account
        return cleaned_data

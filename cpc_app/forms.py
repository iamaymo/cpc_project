from django import forms
from django.db.models import Q
from .models import Clients, Engineers, Networks


def normalize_phone_number(phone_str):
    if not phone_str:
        return ''
    arabic_numerals = {'٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
                       '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'}
    for ar, en in arabic_numerals.items():
        phone_str = phone_str.replace(ar, en)
    return ''.join(c for c in phone_str if c.isdigit())


class RegisterForm(forms.ModelForm):
    network_name = forms.CharField(
        max_length=50,
        label='اسم الشبكة',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
            'placeholder': 'أدخل اسم الشبكة',
        }),
        error_messages={
            'required': 'يرجى إدخال اسم الشبكة.',
            'max_length': 'يجب ألا يتجاوز اسم الشبكة 50 حرفاً.',
        }
    )

    assigned_engineer = forms.ModelChoiceField(
        queryset=Engineers.objects.all(),
        required=False,
        label='المهندس المشرف',
        empty_label='اختر مهندس (اختياري)',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition bg-white',
        })
    )

    class Meta:
        model = Clients
        fields = ['first_name', 'last_name', 'phone_number', 'email', 'username', 'password']
        labels = {
            'first_name': 'الاسم الأول',
            'last_name': 'الاسم الأخير',
            'phone_number': 'رقم الهاتف',
            'email': 'البريد الإلكتروني',
            'username': 'اسم المستخدم',
            'password': 'كلمة المرور',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
                'placeholder': 'أدخل الاسم الأول',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
                'placeholder': 'أدخل الاسم الأخير',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
                'placeholder': '7XXXXXXXX',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
                'placeholder': 'example@domain.com',
            }),
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
                'placeholder': 'أدخل اسم المستخدم',
                'maxlength': '10',
            }),
            'password': forms.PasswordInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
                'placeholder': 'أدخل كلمة المرور',
                'autocomplete': 'new-password',
            }),
        }
        error_messages = {
            'first_name': {
                'required': 'يرجى إدخال الاسم الأول.',
                'max_length': 'يجب ألا يتجاوز الاسم الأول 20 حرفاً.',
            },
            'last_name': {
                'required': 'يرجى إدخال الاسم الأخير.',
                'max_length': 'يجب ألا يتجاوز الاسم الأخير 20 حرفاً.',
            },
            'username': {
                'required': 'يرجى إدخال اسم المستخدم.',
                'max_length': 'يجب ألا يتجاوز اسم المستخدم 10 أحرف.',
            },
            'phone_number': {
                'required': 'يرجى إدخال رقم الهاتف.',
                'max_length': 'يجب ألا يتجاوز رقم الهاتف 15 رقماً.',
            },
            'email': {
                'required': 'يرجى إدخال عنوان البريد الإلكتروني.',
                'invalid': 'يرجى إدخال عنوان بريد إلكتروني صالح.',
            },
            'password': {
                'required': 'يرجى إدخال كلمة المرور.',
            },
        }

    def save(self, commit=True):
        client = super().save(commit=False)
        raw_password = self.cleaned_data.get('password')
        if raw_password:
            client.set_password(raw_password)
        if commit:
            client.save()
        return client


class LoginForm(forms.Form):
    username_or_email = forms.CharField(
        max_length=50,
        label='اسم المستخدم أو البريد الإلكتروني',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
            'placeholder': 'أدخل اسم المستخدم أو البريد الإلكتروني',
            'autocomplete': 'username',
        }),
        error_messages={
            'required': 'يرجى إدخال اسم المستخدم أو البريد الإلكتروني.',
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
        identifier = cleaned_data.get('username_or_email')
        password = cleaned_data.get('password')

        if not identifier or not password:
            return cleaned_data

        identifier = identifier.strip()

        # 1. Search in Clients
        account = Clients.objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).first()
        account_type = 'client'

        # 2. If not found in Clients, search in Engineers
        if not account:
            account = Engineers.objects.filter(
                Q(username__iexact=identifier) | Q(email__iexact=identifier)
            ).first()
            if account:
                account_type = 'engineer'

        # Check account existence
        if not account:
            self.add_error(
                'username_or_email',
                'لا يوجد حساب مسجل باسم المستخدم أو البريد الإلكتروني المدخل.'
            )
            return cleaned_data

        # 3. Verify password
        if not account.check_password(password):
            self.add_error(
                'password',
                'كلمة المرور غير صحيحة، يرجى المحاولة مجدداً.'
            )
            return cleaned_data

        self.account = account
        self.account_type = account_type
        return cleaned_data

from django import forms
from .models import Users


class RegisterForm(forms.ModelForm):
    class Meta:
        model = Users
        fields = ['first_name', 'last_name', 'username', 'email']
        labels = {
            'first_name': 'الاسم الأول',
            'last_name': 'الاسم الأخير',
            'username': 'اسم المستخدم',
            'email': 'البريد الإلكتروني',
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
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
                'placeholder': 'أدخل اسم المستخدم',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
                'placeholder': 'example@domain.com',
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
            },
            'email': {
                'required': 'يرجى إدخال عنوان البريد الإلكتروني.',
                'invalid': 'يرجى إدخال عنوان بريد إلكتروني صالح.',
            },
        }


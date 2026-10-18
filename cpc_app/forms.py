from django import forms
from .models import Clients, Engineers, Networks


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
        fields = ['first_name', 'last_name', 'username', 'phone_number', 'email']
        labels = {
            'first_name': 'الاسم الأول',
            'last_name': 'الاسم الأخير',
            'username': 'اسم المستخدم',
            'phone_number': 'رقم الهاتف',
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
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
                'placeholder': '05xxxxxxxx',
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
        }

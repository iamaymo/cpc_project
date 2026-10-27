from django import forms
from django.db.models import Q
from .models import Users, Product, Client, Bill, BillItem


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


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label='كلمة المرور',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
            'placeholder': 'أدخل كلمة المرور للمستخدم',
            'autocomplete': 'new-password',
        }),
        error_messages={
            'required': 'يرجى إدخال كلمة المرور.',
        }
    )

    class Meta:
        model = Users
        fields = ['full_name', 'phone_number', 'role', 'is_superuser', 'can_manage_products']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
                'placeholder': 'الاسم الرباعي أو الكامل',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
                'placeholder': 'مثال: 7XXXXXXXX',
                'dir': 'ltr',
            }),
            'role': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition bg-white',
            }),
            'is_superuser': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-[#1b313e] border-gray-300 rounded focus:ring-[#1b313e]',
            }),
            'can_manage_products': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-[#1b313e] border-gray-300 rounded focus:ring-[#1b313e]',
            }),
        }

    def clean_phone_number(self):
        phone_input = self.cleaned_data.get('phone_number')
        cleaned_phone = normalize_phone_number(phone_input)
        if not cleaned_phone:
            raise forms.ValidationError('يرجى إدخال رقم هاتف صالح.')
        if Users.objects.filter(phone_number=cleaned_phone).exists():
            raise forms.ValidationError('رقم الهاتف مسجل مسبقاً لمستخدم آخر.')
        return cleaned_phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.phone_number
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'initial_count', 'condition']
        labels = {
            'name': 'اسم المنتج',
            'price': 'السعر',
            'initial_count': 'الكمية المدخلة',
            'condition': 'حالة المنتج',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition',
                'placeholder': 'أدخل اسم المنتج',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition font-mono',
                'placeholder': 'السعر',
                'step': '1',
                'min': '0',
            }),
            'initial_count': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition font-mono',
                'placeholder': 'الكمية المتوفرة',
                'min': '0',
            }),
            'condition': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1b313e] focus:border-[#1b313e] focus:outline-none transition bg-white',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('يرجى إدخال اسم المنتج.')
        qs = Product.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f'المنتج "{name}" موجود مسبقاً، لا يمكن تكرار اسم المنتج.')
        return name


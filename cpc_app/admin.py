from django import forms
from django.contrib import admin
from .models import Users, TabPermission, Product, Client, Bill, BillItem, ProductAuditLog


class TabPermissionInline(admin.TabularInline):
    model = TabPermission
    extra = 0
    fields = ('tab_name', 'permission_level')


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
    inlines = [TabPermissionInline]
    list_display = ('full_name', 'phone_number', 'username', 'role', 'is_superuser', 'can_manage_products', 'add_at')
    list_filter = ('role', 'is_superuser', 'can_manage_products', 'add_at')
    search_fields = ('full_name', 'phone_number', 'username')
    readonly_fields = ('username', 'add_at')
    fields = ('full_name', 'phone_number', 'password', 'role', 'is_superuser', 'can_manage_products', 'username', 'add_at')

    def save_model(self, request, obj, form, change):
        obj.username = obj.phone_number
        new_password = form.cleaned_data.get('password')
        if new_password:
            obj.set_password(new_password)
        super().save_model(request, obj, form, change)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'initial_count', 'available_count', 'sold_count', 'condition', 'is_active', 'created_at')
    list_filter = ('is_active', 'condition', 'created_at')
    search_fields = ('name',)


class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 1


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('bill_number', 'id', 'bill_type', 'client', 'total_amount', 'created_by', 'created_at')
    list_filter = ('bill_type', 'created_at', 'created_by')
    search_fields = ('bill_number', 'client__name', 'client__phone', 'id')
    inlines = [BillItemInline]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'network_name', 'created_at')
    search_fields = ('name', 'phone', 'network_name')


@admin.register(ProductAuditLog)
class ProductAuditLogAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'action_type', 'user_name', 'changes', 'reason', 'created_at')
    list_filter = ('action_type', 'created_at', 'user')
    search_fields = ('product_name', 'user_name', 'changes')
    readonly_fields = ('product', 'product_name', 'action_type', 'user', 'user_name', 'changes', 'reason', 'created_at')


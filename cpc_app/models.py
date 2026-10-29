from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class RoleChoices(models.TextChoices):
    ENGINEER = 'ENGINEER', 'مهندس'
    SALES = 'SALES', 'مبيعات'
    ADMIN = 'ADMIN', 'إدارة'
    ACCOUNTING = 'ACCOUNTING', 'حسابات'


class Users(models.Model):
    full_name = models.CharField(max_length=100, verbose_name="الاسم الكامل")
    phone_number = models.CharField(max_length=15, unique=True, verbose_name="رقم الهاتف")
    username = models.CharField(max_length=15, unique=True, blank=True, verbose_name="اسم المستخدم")
    password = models.CharField(max_length=128, verbose_name="كلمة المرور")
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.ENGINEER,
        verbose_name="الدور / الفريق"
    )
    is_superuser = models.BooleanField(default=False, verbose_name="مدير النظام")
    can_manage_products = models.BooleanField(default=False, verbose_name="صلاحية إضافة وتعديل المنتجات")
    add_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")

    class Meta:
        db_table = 'USERS'
        verbose_name = 'مستخدم'
        verbose_name_plural = 'المستخدمون'

    def save(self, *args, **kwargs):
        if not self.username or self.username != self.phone_number:
            self.username = self.phone_number
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        if not self.password:
            return False
        if check_password(raw_password, self.password):
            return True
        return self.password == raw_password

    def get_allowed_tabs(self):
        """Returns list of tab names this user can access (either read or full)."""
        all_tabs = ['sales', 'services', 'bills', 'accounts', 'reports']
        permissions = self.tab_permissions.all()
        if not permissions.exists():
            return all_tabs
        # Allow tab if permission is 'all' or 'read'
        return [p.tab_name for p in permissions if p.permission_level in ['all', 'read']]

    def get_tab_permission_level(self, tab_name):
        """Returns 'all', 'read', or 'none'."""
        perm = self.tab_permissions.filter(tab_name=tab_name).first()
        if not perm:
            return 'all'  # default is all
        return perm.permission_level

    def can_edit_products(self):
        """Superuser or user with can_manage_products flag."""
        return self.is_superuser or self.can_manage_products

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"


class TabPermission(models.Model):
    TAB_CHOICES = [
        ('sales', 'المبيعات'),
        ('services', 'الخدمات'),
        ('bills', 'الفواتير'),
        ('accounts', 'الحسابات'),
        ('reports', 'التقارير'),
    ]

    PERMISSION_CHOICES = [
        ('all', 'شامل (All)'),
        ('read', 'قراءة فقط (Read only)'),
        ('none', 'لا يوجد (None)'),
    ]

    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name='tab_permissions',
        verbose_name="المستخدم"
    )
    tab_name = models.CharField(max_length=20, choices=TAB_CHOICES, verbose_name="التبويب")
    permission_level = models.CharField(
        max_length=10,
        choices=PERMISSION_CHOICES,
        default='all',
        verbose_name="مستوى الصلاحية"
    )

    class Meta:
        db_table = 'TAB_PERMISSIONS'
        verbose_name = 'صلاحية تبويب'
        verbose_name_plural = 'صلاحيات التبويبات'
        unique_together = ('user', 'tab_name')

    def __str__(self):
        return f"{self.user.full_name} - {self.get_tab_name_display()} [{self.get_permission_level_display()}]"


class ProductCondition(models.TextChoices):
    NEW = 'new', 'جديد'
    USED = 'used', 'مستخدم'


class Product(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="اسم المنتج")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="السعر")
    initial_count = models.PositiveIntegerField(default=0, verbose_name="الكمية الكلية / المدخلة")
    condition = models.CharField(
        max_length=10,
        choices=ProductCondition.choices,
        default=ProductCondition.NEW,
        verbose_name="حالة المنتج"
    )
    is_active = models.BooleanField(default=True, verbose_name="حالة التفعيل")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        db_table = 'PRODUCTS'
        verbose_name = 'منتج'
        verbose_name_plural = 'المنتجات'
        ordering = ['-created_at']

    @property
    def sold_count(self):
        sales_sold = self.bill_items.filter(bill__bill_type='sales').aggregate(models.Sum('quantity'))['quantity__sum'] or 0
        refunded = self.bill_items.filter(bill__bill_type='refund').aggregate(models.Sum('quantity'))['quantity__sum'] or 0
        return max(0, sales_sold - refunded)

    @property
    def available_count(self):
        """Current real available stock: initial count minus total sold in bills."""
        return max(0, self.initial_count - self.sold_count)

    def __str__(self):
        return f"{self.name} ({self.get_condition_display()}) - {self.price} ر.ي"


class Client(models.Model):
    name = models.CharField(max_length=150, verbose_name="اسم العميل")
    phone = models.CharField(max_length=20, verbose_name="رقم الهاتف")
    network_name = models.CharField(max_length=100, blank=True, verbose_name="اسم الشبكة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")

    class Meta:
        db_table = 'CLIENTS'
        verbose_name = 'عميل'
        verbose_name_plural = 'العملاء'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.phone}"


class Bill(models.Model):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='bills',
        verbose_name="العميل"
    )
    created_by = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_bills',
        verbose_name="أنشئت بواسطة"
    )
    BILL_TYPES = [
        ('sales', 'فاتورة مبيعات'),
        ('services', 'فاتورة خدمات'),
        ('refund', 'فاتورة مرتجع'),
    ]
    bill_type = models.CharField(
        max_length=20,
        choices=BILL_TYPES,
        default='sales',
        verbose_name="نوع الفاتورة"
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="المبلغ الإجمالي")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        db_table = 'BILLS'
        verbose_name = 'فاتورة'
        verbose_name_plural = 'الفواتير'
        ordering = ['-created_at']

    def calculate_total(self):
        total = sum(item.total_price for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total

    def __str__(self):
        return f"فاتورة #{self.id} - {self.client.name} ({self.created_at.strftime('%Y-%m-%d')})"


class BillItem(models.Model):
    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="الفاتورة"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='bill_items',
        verbose_name="المنتج"
    )
    product_name = models.CharField(max_length=200, verbose_name="اسم المنتج وقت البيع")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="السعر الفردي")
    condition = models.CharField(max_length=10, choices=ProductCondition.choices, verbose_name="الحالة")
    quantity = models.PositiveIntegerField(default=1, verbose_name="الكمية")

    class Meta:
        db_table = 'BILL_ITEMS'
        verbose_name = 'بند فاتورة'
        verbose_name_plural = 'بنود الفواتير'

    @property
    def total_price(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class ProductAuditLog(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name="المنتج"
    )
    product_name = models.CharField(max_length=200, verbose_name="اسم المنتج")
    user = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="المستخدم الذي قام بالتعديل"
    )
    user_name = models.CharField(max_length=100, verbose_name="اسم المستخدم")
    ACTION_TYPES = [
        ('edit', 'تعديل بيانات'),
        ('restock', 'توريد كمية جديدة'),
        ('refund', 'مرتجع مبيعات'),
    ]
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_TYPES,
        default='edit',
        verbose_name="نوع العملية"
    )
    changes = models.TextField(verbose_name="تفاصيل التعديلات")
    reason = models.CharField(max_length=255, blank=True, verbose_name="سبب التعديل")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ ووقت التعديل")

    class Meta:
        db_table = 'PRODUCT_AUDIT_LOGS'
        verbose_name = 'سجل تعديل منتج'
        verbose_name_plural = 'سجلات تعديلات المنتجات'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product_name} تعديل بواسطة {self.user_name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


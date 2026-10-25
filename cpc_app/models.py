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

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

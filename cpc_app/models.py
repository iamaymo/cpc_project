from django.db import models

# Create your models here.


class Users(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    email = models.EmailField()
    username = models.CharField()
    user_type = models.CharField(default='NORMAL')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'USERS'

    def __str__(self):
        return self.username

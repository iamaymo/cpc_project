from django.db import models
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

# Create your models here.


class Clients(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=10, unique=True)
    phone_number = models.CharField(max_length=15)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'CLIENTS'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"


class Engineers(models.Model):
    full_name = models.CharField(max_length=50)
    username = models.CharField(max_length=10, unique=True)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    number_of_networks = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'ENGINEERS'

    def __str__(self):
        return self.full_name


class Networks(models.Model):
    network_name = models.CharField(max_length=50)
    owner = models.ForeignKey(Clients, on_delete=models.CASCADE, related_name='networks')
    assigned_engineer = models.ForeignKey(
        Engineers,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='networks'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'NETWORKS'

    def __str__(self):
        return self.network_name


@receiver(pre_save, sender=Networks)
def track_old_assigned_engineer(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_network = sender.objects.get(pk=instance.pk)
            instance._old_assigned_engineer_id = old_network.assigned_engineer_id
        except sender.DoesNotExist:
            instance._old_assigned_engineer_id = None
    else:
        instance._old_assigned_engineer_id = None


@receiver(post_save, sender=Networks)
def update_engineer_network_count_on_save(sender, instance, **kwargs):
    old_eng_id = getattr(instance, '_old_assigned_engineer_id', None)
    new_eng_id = instance.assigned_engineer_id

    # If the network was previously assigned to another engineer, recalculate the old engineer's count
    if old_eng_id and old_eng_id != new_eng_id:
        try:
            old_eng = Engineers.objects.get(pk=old_eng_id)
            old_eng.number_of_networks = old_eng.networks.count()
            old_eng.save(update_fields=['number_of_networks'])
        except Engineers.DoesNotExist:
            pass

    # Recalculate the current engineer's count
    if new_eng_id:
        try:
            new_eng = Engineers.objects.get(pk=new_eng_id)
            new_eng.number_of_networks = new_eng.networks.count()
            new_eng.save(update_fields=['number_of_networks'])
        except Engineers.DoesNotExist:
            pass


@receiver(post_delete, sender=Networks)
def update_engineer_network_count_on_delete(sender, instance, **kwargs):
    if instance.assigned_engineer_id:
        try:
            eng = Engineers.objects.get(pk=instance.assigned_engineer_id)
            eng.number_of_networks = eng.networks.count()
            eng.save(update_fields=['number_of_networks'])
        except Engineers.DoesNotExist:
            pass
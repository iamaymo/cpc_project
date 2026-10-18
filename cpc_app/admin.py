from django.contrib import admin
from .models import Clients, Engineers, Networks


@admin.register(Clients)
class ClientsAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'phone_number', 'joined_at')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')
    list_filter = ('joined_at',)


@admin.register(Engineers)
class EngineersAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'email', 'phone_number', 'number_of_networks', 'joined_at')
    search_fields = ('username', 'full_name', 'email', 'phone_number')
    list_filter = ('joined_at',)


@admin.register(Networks)
class NetworksAdmin(admin.ModelAdmin):
    list_display = ('network_name', 'owner', 'assigned_engineer', 'created_at')
    search_fields = ('network_name', 'owner__username', 'assigned_engineer__full_name')
    list_filter = ('created_at',)

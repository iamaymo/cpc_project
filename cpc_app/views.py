from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .forms import RegisterForm
from .models import Networks

# Create your views here.


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                client = form.save()
                network_name = form.cleaned_data['network_name']
                assigned_engineer = form.cleaned_data.get('assigned_engineer')
                Networks.objects.create(
                    network_name=network_name,
                    owner=client,
                    assigned_engineer=assigned_engineer,
                )
                if assigned_engineer:
                    assigned_engineer.number_of_networks = assigned_engineer.networks.count()
                    assigned_engineer.save()
            messages.success(request, 'تم إنشاء الحساب والشبكة بنجاح!')
            return redirect('register')
    else:
        form = RegisterForm()
    context = {"form": form}
    return render(request, 'register.html', context)

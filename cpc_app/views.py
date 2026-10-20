from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .forms import RegisterForm, LoginForm
from .models import Clients, Engineers, Networks

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


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            account = form.account
            account_type = form.account_type

            request.session['user_id'] = account.id
            request.session['user_type'] = account_type
            request.session['username'] = account.username

            display_name = (
                f"{account.first_name} {account.last_name}"
                if hasattr(account, 'first_name')
                else account.full_name
            )
            request.session['full_name'] = display_name

            messages.success(request, f'مرحباً بك {display_name}! تم تسجيل الدخول بنجاح.')
            return render(request, 'login.html', {
                'form': LoginForm(),
                'logged_in_user': account,
                'user_type': account_type,
            })
    else:
        form = LoginForm()

    logged_in_user = None
    user_type = None
    if 'user_id' in request.session:
        user_id = request.session.get('user_id')
        user_type = request.session.get('user_type')
        if user_type == 'client':
            logged_in_user = Clients.objects.filter(id=user_id).first()
        elif user_type == 'engineer':
            logged_in_user = Engineers.objects.filter(id=user_id).first()

    context = {
        'form': form,
        'logged_in_user': logged_in_user,
        'user_type': user_type,
    }
    return render(request, 'login.html', context)


def logout_view(request):
    request.session.flush()
    messages.info(request, 'تم تسجيل الخروج بنجاح.')
    return redirect('login')

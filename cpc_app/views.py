from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import LoginForm
from .models import Users


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            account = form.account

            request.session['user_id'] = account.id
            request.session['username'] = account.username
            request.session['full_name'] = account.full_name
            request.session['role'] = account.role
            request.session['role_display'] = account.get_role_display()

            messages.success(request, f'مرحباً بك {account.full_name}! تم تسجيل الدخول بنجاح.')
            return render(request, 'login.html', {
                'form': LoginForm(),
                'logged_in_user': account,
            })
    else:
        form = LoginForm()

    logged_in_user = None
    if 'user_id' in request.session:
        user_id = request.session.get('user_id')
        logged_in_user = Users.objects.filter(id=user_id).first()
        if not logged_in_user:
            # Stale session
            request.session.flush()

    context = {
        'form': form,
        'logged_in_user': logged_in_user,
    }
    return render(request, 'login.html', context)


def logout_view(request):
    request.session.flush()
    messages.info(request, 'تم تسجيل الخروج بنجاح.')
    return redirect('login')

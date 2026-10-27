import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from .forms import LoginForm, UserCreateForm, ProductForm
from .models import Users, TabPermission, Product, Client, Bill, BillItem, ProductAuditLog


def login_required_custom(view_func):
    """Decorator: redirects to login if no session."""
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            messages.warning(request, 'يرجى تسجيل الدخول أولاً.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def superuser_required(view_func):
    """Decorator: only superusers can access."""
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            messages.warning(request, 'يرجى تسجيل الدخول أولاً.')
            return redirect('login')
        user = Users.objects.filter(id=request.session['user_id']).first()
        if not user or not user.is_superuser:
            messages.error(request, 'ليس لديك صلاحية الوصول لهذه الصفحة.')
            return redirect('portal')
        return view_func(request, *args, **kwargs)
    return wrapper


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
            request.session['is_superuser'] = account.is_superuser

            messages.success(request, f'مرحباً بك {account.full_name}! تم تسجيل الدخول بنجاح.')
            return redirect('portal')
    else:
        form = LoginForm()

    if 'user_id' in request.session:
        return redirect('portal')

    context = {
        'form': form,
    }
    return render(request, 'login.html', context)


def logout_view(request):
    request.session.flush()
    messages.info(request, 'تم تسجيل الخروج بنجاح.')
    return redirect('login')


def dashboard_redirect(request):
    """Redirect legacy dashboard url to portal."""
    query = request.META.get('QUERY_STRING')
    target = '/portal/' + (f'?{query}' if query else '')
    return redirect(target)


@login_required_custom
def dashboard_view(request):
    user = Users.objects.filter(id=request.session['user_id']).first()
    if not user:
        request.session.flush()
        return redirect('login')

    allowed_tabs = user.get_allowed_tabs()
    active_tab = request.GET.get('tab', '')

    if not active_tab or active_tab not in allowed_tabs:
        active_tab = allowed_tabs[0] if allowed_tabs else ''

    all_tabs = [
        {'id': 'sales', 'name': 'المبيعات', 'icon': 'cart'},
        {'id': 'services', 'name': 'الخدمات', 'icon': 'wrench'},
        {'id': 'bills', 'name': 'الفواتير', 'icon': 'document-text'},
        {'id': 'accounts', 'name': 'الحسابات', 'icon': 'calculator'},
        {'id': 'reports', 'name': 'التقارير', 'icon': 'chart'},
    ]

    visible_tabs = [tab for tab in all_tabs if tab['id'] in allowed_tabs]

    # Tab permission levels
    active_tab_perm = user.get_tab_permission_level(active_tab) if active_tab else 'none'
    bills_perm = user.get_tab_permission_level('bills')
    sales_perm = user.get_tab_permission_level('sales')
    services_perm = user.get_tab_permission_level('services')

    can_create_sales_bill = user.is_superuser or (sales_perm == 'all' and bills_perm == 'all')
    can_create_services_bill = user.is_superuser or (services_perm == 'all' and bills_perm == 'all')
    can_create_any_bill = can_create_sales_bill or can_create_services_bill

    # Data for Sales Tab - sort available first, out of stock (available == 0) last
    raw_products = list(Product.objects.all().order_by('-created_at'))
    products = sorted(raw_products, key=lambda p: 1 if p.available_count == 0 else 0)
    product_form = ProductForm()

    # Data for Bills Tab
    bills = Bill.objects.select_related('client', 'created_by').prefetch_related('items__product').order_by('-created_at')
    clients = Client.objects.all().order_by('name')

    # Serialized products for bills autocomplete/selection modal
    products_data = [
        {
            'id': p.id,
            'name': p.name,
            'price': float(p.price),
            'available': p.available_count,
            'condition': p.condition,
            'condition_display': p.get_condition_display(),
        }
        for p in products
    ]

    # Serialized clients for phone number autocomplete
    clients_data = [
        {
            'id': c.id,
            'name': c.name,
            'phone': c.phone,
            'network_name': c.network_name or '',
        }
        for c in clients
    ]

    context = {
        'user': user,
        'tabs': visible_tabs,
        'active_tab': active_tab,
        'active_tab_perm': active_tab_perm,
        'is_superuser': user.is_superuser,
        'can_manage_products': user.can_edit_products(),
        'can_create_sales_bill': can_create_sales_bill,
        'can_create_services_bill': can_create_services_bill,
        'can_create_any_bill': can_create_any_bill,
        'sales_perm': sales_perm,
        'services_perm': services_perm,
        'bills_perm': bills_perm,
        'products': products,
        'product_form': product_form,
        'bills': bills,
        'clients': clients,
        'products_json': json.dumps(products_data, ensure_ascii=False),
        'clients_json': json.dumps(clients_data, ensure_ascii=False),
    }
    return render(request, 'dashboard.html', context)


@login_required_custom
def add_product_view(request):
    user = Users.objects.filter(id=request.session['user_id']).first()
    if not user:
        return redirect('login')

    # Check permission
    sales_perm = user.get_tab_permission_level('sales')
    if sales_perm != 'all' or not user.can_edit_products():
        messages.error(request, 'ليس لديك صلاحية إضافة أو تعديل المنتجات.')
        return redirect('/portal/?tab=sales')

    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            if not user.is_superuser:
                product.initial_count = 0
            product.save()
            messages.success(request, f'تمت إضافة المنتج "{product.name}" بنجاح.')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f'{err}')

    return redirect('/portal/?tab=sales')


@login_required_custom
def edit_product_view(request, product_id):
    user = Users.objects.filter(id=request.session['user_id']).first()
    if not user:
        return redirect('login')

    sales_perm = user.get_tab_permission_level('sales')
    if sales_perm != 'all' or not user.can_edit_products():
        messages.error(request, 'ليس لديك صلاحية تعديل المنتجات.')
        return redirect('/portal/?tab=sales')

    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        price_str = request.POST.get('price', '').strip()
        condition = request.POST.get('condition', '').strip()
        initial_count_str = request.POST.get('initial_count', '').strip()
        reason = request.POST.get('audit_reason', '').strip()

        if not name:
            messages.error(request, 'اسم المنتج مطلوب.')
            return redirect('/portal/?tab=sales')

        # Check unique name excluding this product
        if Product.objects.filter(name__iexact=name).exclude(id=product.id).exists():
            messages.error(request, f'الاسم "{name}" مسجل مسبقاً لمنتج آخر.')
            return redirect('/portal/?tab=sales')

        try:
            new_price = Decimal(price_str)
        except Exception:
            new_price = product.price

        changes_list = []
        if name != product.name:
            changes_list.append(f"الاسم: من '{product.name}' إلى '{name}'")
        if new_price != product.price:
            changes_list.append(f"السعر: من '{product.price}' إلى '{new_price}'")
        if condition and condition != product.condition:
            changes_list.append(f"الحالة: من '{product.get_condition_display()}' إلى '{condition}'")

        # Edit count - allow admin, or user if allowed
        if user.is_superuser and initial_count_str:
            try:
                new_count = int(initial_count_str)
                if new_count != product.initial_count:
                    changes_list.append(f"الكمية الكلية: من '{product.initial_count}' إلى '{new_count}'")
                    product.initial_count = new_count
            except ValueError:
                pass

        if changes_list:
            changes_text = " | ".join(changes_list)
            # Apply changes
            product.name = name
            product.price = new_price
            if condition:
                product.condition = condition
            product.save()

            # Record audit log
            ProductAuditLog.objects.create(
                product=product,
                product_name=product.name,
                user=user,
                user_name=user.full_name,
                changes=changes_text,
                reason=reason or "تعديل بيانات المنتج",
            )
            messages.success(request, f'تم تعديل المنتج "{product.name}" بنجاح وتسجيل التغييرات في سجل التدقيق.')
        else:
            messages.info(request, 'لم يتم إجراء أي تغييرات على المنتج.')

    return redirect('/portal/?tab=sales')


@login_required_custom
def bill_detail_json_view(request, bill_id):
    """Return JSON details for print and modal viewer."""
    user = Users.objects.filter(id=request.session['user_id']).first()
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    bill = get_object_or_404(Bill.objects.select_related('client', 'created_by').prefetch_related('items'), id=bill_id)
    items_data = [
        {
            'name': item.product_name,
            'price': float(item.price),
            'quantity': item.quantity,
            'total': float(item.total_price),
            'condition': item.get_condition_display(),
        }
        for item in bill.items.all()
    ]

    return JsonResponse({
        'id': bill.id,
        'created_at': bill.created_at.strftime('%Y-%m-%d %H:%M'),
        'client_name': bill.client.name,
        'client_phone': bill.client.phone,
        'network_name': bill.client.network_name or '—',
        'created_by': bill.created_by.full_name if bill.created_by else 'النظام',
        'total_amount': float(bill.total_amount),
        'notes': bill.notes or '',
        'items': items_data,
    })




@login_required_custom
def create_bill_view(request):
    user = Users.objects.filter(id=request.session['user_id']).first()
    if not user:
        return redirect('login')

    # Check tab permission
    bills_perm = user.get_tab_permission_level('bills')
    sales_perm = user.get_tab_permission_level('sales')
    services_perm = user.get_tab_permission_level('services')

    can_create_sales_bill = user.is_superuser or (sales_perm == 'all' and bills_perm == 'all')
    can_create_services_bill = user.is_superuser or (services_perm == 'all' and bills_perm == 'all')

    if not can_create_sales_bill and not can_create_services_bill:
        messages.error(request, 'ليس لديك صلاحية لإنشاء الفواتير.')
        return redirect('portal')

    if request.method == 'POST':
        bill_type = request.POST.get('bill_type', 'sales')  # 'sales' or 'services'

        if bill_type == 'sales' and not can_create_sales_bill:
            messages.error(request, 'ليس لديك صلاحية لإنشاء فواتير المبيعات أو أن قسم المنتجات مقفل.')
            return redirect('portal')

        if bill_type == 'services' and not can_create_services_bill:
            messages.error(request, 'ليس لديك صلاحية لإنشاء فواتير الخدمات أو أن قسم الخدمات مقفل.')
            return redirect('portal')
        client_name = request.POST.get('client_name', '').strip()
        client_phone = request.POST.get('client_phone', '').strip()
        network_name = request.POST.get('network_name', '').strip()

        if not client_name or not client_phone:
            messages.error(request, 'يرجى إدخال اسم العميل ورقم هاتفه.')
            return redirect(request.META.get('HTTP_REFERER', '/portal/?tab=' + bill_type))

        with transaction.atomic():
            # Get or create client
            client, created = Client.objects.get_or_create(
                phone=client_phone,
                defaults={
                    'name': client_name,
                    'network_name': network_name
                }
            )
            if not created:
                if client_name:
                    client.name = client_name
                if network_name:
                    client.network_name = network_name
                client.save()

            if bill_type == 'services':
                service_description = request.POST.get('service_description', '').strip()
                service_cost_str = request.POST.get('service_cost', '0')
                if not service_description:
                    messages.error(request, 'يرجى إدخال تفاصيل وبيان الخدمة.')
                    return redirect('/portal/?tab=services')

                try:
                    service_cost = Decimal(service_cost_str)
                    if service_cost <= 0:
                        service_cost = Decimal('0')
                except Exception:
                    service_cost = Decimal('0')

                bill = Bill.objects.create(
                    client=client,
                    created_by=user,
                    total_amount=service_cost,
                    notes=f"خدمة: {service_description}",
                )

                # Optional placeholder product for service if needed, or bill with notes
                # To maintain integrity with items:
                # We can create a BillItem referencing or just keep bill total with notes
                # Let's find or create a general service virtual product:
                service_product, _ = Product.objects.get_or_create(
                    name=service_description[:190],
                    defaults={
                        'price': service_cost,
                        'initial_count': 999999,
                        'condition': 'new'
                    }
                )
                BillItem.objects.create(
                    bill=bill,
                    product=service_product,
                    product_name=service_description,
                    price=service_cost,
                    condition='new',
                    quantity=1,
                )
            else:
                # Sales product bill
                product_id = request.POST.get('product_id')
                quantity_str = request.POST.get('quantity', '1')

                if not product_id:
                    messages.error(request, 'يرجى اختيار المنتج المراد بيعه.')
                    return redirect(request.META.get('HTTP_REFERER', '/portal/?tab=sales'))

                product = Product.objects.filter(id=product_id).first()
                if not product:
                    messages.error(request, 'المنتج المحدد غير موجود.')
                    return redirect(request.META.get('HTTP_REFERER', '/portal/?tab=sales'))

                try:
                    quantity = int(quantity_str)
                    if quantity <= 0:
                        quantity = 1
                except ValueError:
                    quantity = 1

                if product.available_count <= 0:
                    messages.error(request, f'المنتج "{product.name}" غير متوفر (نفدت الكمية). لا يمكن إنشاء فاتورة له.')
                    return redirect(request.META.get('HTTP_REFERER', '/portal/?tab=sales'))

                if product.available_count < quantity:
                    messages.error(request, f'الكمية المتوفرة من "{product.name}" ({product.available_count}) غير كافية لطلب كمية ({quantity}).')
                    return redirect(request.META.get('HTTP_REFERER', '/portal/?tab=sales'))

                bill = Bill.objects.create(
                    client=client,
                    created_by=user,
                    total_amount=Decimal(product.price) * Decimal(quantity),
                )

                BillItem.objects.create(
                    bill=bill,
                    product=product,
                    product_name=product.name,
                    price=product.price,
                    condition=product.condition,
                    quantity=quantity,
                )

            bill.calculate_total()

        messages.success(request, f'تم إنشاء الفاتورة رقم #{bill.id} للعميل "{client.name}" بنجاح.')
        return redirect('/portal/?tab=bills')

    return redirect('portal')


@superuser_required
def admin_permissions_view(request):
    user = Users.objects.filter(id=request.session['user_id']).first()
    users = Users.objects.all().order_by('full_name')

    all_tabs = [
        {'id': 'sales', 'name': 'المبيعات'},
        {'id': 'services', 'name': 'الخدمات'},
        {'id': 'bills', 'name': 'الفواتير'},
        {'id': 'accounts', 'name': 'الحسابات'},
        {'id': 'reports', 'name': 'التقارير'},
    ]

    new_user_form = UserCreateForm()

    users_permissions = []
    for u in users:
        tab_perms = []
        for tab in all_tabs:
            level = u.get_tab_permission_level(tab['id'])
            tab_perms.append({
                'tab_id': tab['id'],
                'tab_name': tab['name'],
                'level': level,
                'field_name': f'perm_{u.id}_{tab["id"]}',
            })
        users_permissions.append({
            'user': u,
            'tab_perms': tab_perms,
        })

    context = {
        'user': user,
        'users_permissions': users_permissions,
        'all_tabs': all_tabs,
        'is_superuser': user.is_superuser,
        'new_user_form': new_user_form,
    }
    return render(request, 'admin_permissions.html', context)


@superuser_required
def add_user_view(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            messages.success(request, f'تمت إضافة المستخدم "{new_user.full_name}" بنجاح.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    return redirect('admin_permissions')


@superuser_required
def update_permissions_view(request):
    if request.method != 'POST':
        return redirect('admin_permissions')

    users = Users.objects.all()
    all_tab_ids = ['sales', 'bills', 'services', 'accounts', 'reports']

    for u in users:
        # Also update can_manage_products checkbox
        u.can_manage_products = f'can_manage_products_{u.id}' in request.POST
        u.save(update_fields=['can_manage_products'])

        for tab_id in all_tab_ids:
            field_name = f'perm_{u.id}_{tab_id}'
            level = request.POST.get(field_name, 'all')
            if level not in ['all', 'read', 'none']:
                level = 'all'

            TabPermission.objects.update_or_create(
                user=u,
                tab_name=tab_id,
                defaults={'permission_level': level}
            )

    messages.success(request, 'تم حفظ مستويات الصلاحيات بنجاح.')
    return redirect('admin_permissions')

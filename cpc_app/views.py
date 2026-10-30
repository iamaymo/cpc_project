import json
import re
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
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
    can_create_refund_bill = user.is_superuser or (sales_perm == 'all') or (services_perm == 'all') or (bills_perm == 'all')
    can_create_any_bill = can_create_sales_bill or can_create_services_bill or can_create_refund_bill

    # Data for Sales Tab - sort active & available first, out of stock second, inactive last
    raw_products = list(Product.objects.all().order_by('-created_at'))
    products = sorted(raw_products, key=lambda p: (0 if p.is_active else 2, 1 if p.available_count == 0 else 0))
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
            'is_active': p.is_active,
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

    # Data for Reports Tab
    audit_logs = ProductAuditLog.objects.select_related('product', 'user').order_by('-created_at')
    report_stats = {
        'total_logs': audit_logs.count(),
        'restock_logs': audit_logs.filter(action_type='restock').count(),
        'edit_logs': audit_logs.filter(action_type='edit').count(),
        'refund_logs': audit_logs.filter(action_type='refund').count(),
        'total_bills': bills.count(),
    }

    context = {
        'user': user,
        'tabs': visible_tabs,
        'active_tab': active_tab,
        'active_tab_perm': active_tab_perm,
        'is_superuser': user.is_superuser,
        'can_manage_products': user.can_edit_products(),
        'can_create_sales_bill': can_create_sales_bill,
        'can_create_services_bill': can_create_services_bill,
        'can_create_refund_bill': can_create_refund_bill,
        'can_create_any_bill': can_create_any_bill,
        'sales_perm': sales_perm,
        'services_perm': services_perm,
        'bills_perm': bills_perm,
        'products': products,
        'product_form': product_form,
        'bills': bills,
        'clients': clients,
        'audit_logs': audit_logs,
        'report_stats': report_stats,
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
        name = request.POST.get('name', '').strip() or product.name
        price_str = request.POST.get('price', '').strip()
        condition = request.POST.get('condition', '').strip() or product.condition
        initial_count_str = request.POST.get('initial_count', '').strip()
        add_quantity_str = request.POST.get('add_quantity', '0').strip()
        reason = request.POST.get('audit_reason', '').strip()
        
        # Check active status toggle switch
        is_active_val = request.POST.get('is_active')
        new_is_active = bool(is_active_val)

        # Check unique name excluding this product
        if name and name != product.name:
            if Product.objects.filter(name__iexact=name).exclude(id=product.id).exists():
                messages.error(request, f'الاسم "{name}" مسجل مسبقاً لمنتج آخر.')
                return redirect('/portal/?tab=sales')

        try:
            new_price = Decimal(price_str) if price_str else product.price
        except Exception:
            new_price = product.price

        changes_list = []
        action_type = 'edit'

        if name != product.name:
            changes_list.append(f"الاسم: من '{product.name}' إلى '{name}'")
        if new_price != product.price:
            changes_list.append(f"السعر: من '{product.price}' إلى '{new_price}'")
        if condition and condition != product.condition:
            changes_list.append(f"الحالة: من '{product.get_condition_display()}' إلى '{condition}'")
        if new_is_active != product.is_active:
            status_desc = "تفعيل المنتج" if new_is_active else "إيقاف المنتج مؤقتاً"
            changes_list.append(f"حالة التفعيل: {status_desc}")

        # Handle adding new quantity (accessible to all with product edit permission)
        add_quantity = 0
        if add_quantity_str:
            try:
                add_quantity = int(add_quantity_str)
                if add_quantity < 0:
                    add_quantity = 0
            except ValueError:
                add_quantity = 0

        if add_quantity > 0:
            old_initial = product.initial_count
            product.initial_count += add_quantity
            changes_list.append(f"إضافة كمية واردة للمخزون: +{add_quantity} قطعة (الكمية الكلية من {old_initial} إلى {product.initial_count} قطعة)")
            if not any(k in changes_list[0] for k in ["الاسم", "السعر", "الحالة", "حالة التفعيل"]):
                action_type = 'restock'

        # Edit count directly - allow superuser only
        if user.is_superuser and initial_count_str and add_quantity == 0:
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
            product.is_active = new_is_active
            product.save()

            # Record audit log - auto-generate reason if user left it blank
            if not reason:
                if action_type == 'restock':
                    reason = f"توريد كمية واردة جديدة للمخزون (+{add_quantity} قطعة)"
                elif new_is_active != product.is_active and len(changes_list) == 1:
                    reason = "تغيير حالة تفعيل المنتج"
                else:
                    reason = "تعديل بيانات المنتج"

            ProductAuditLog.objects.create(
                product=product,
                product_name=product.name,
                action_type=action_type,
                user=user,
                user_name=user.full_name,
                changes=changes_text,
                reason=reason,
            )
            messages.success(request, f'تم تحديث المنتج "{product.name}" بنجاح وتوثيق العملية في سجل التقارير.')
        else:
            messages.info(request, 'لم يتم إجراء أي تغييرات على المنتج.')

    return redirect('/portal/?tab=sales')


@login_required_custom
def product_restock_history_json_view(request, product_id):
    """API to get restock supply history for a specific product."""
    user = Users.objects.filter(id=request.session['user_id']).first()
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    product = get_object_or_404(Product, id=product_id)

    # Fetch audit logs matching restock for this product
    logs = ProductAuditLog.objects.filter(
        Q(product=product) | Q(product_name=product.name),
        Q(action_type='restock') | Q(changes__icontains='إضافة كمية واردة') | Q(changes__icontains='توريد')
    ).order_by('-created_at')

    history_data = []
    total_restocked_qty = 0

    for log in logs:
        # Extract added quantity via regex: +10 قطعة or +5
        match = re.search(r'\+(\d+)\s*(?:قطعة)?', log.changes)
        qty = int(match.group(1)) if match else None
        if qty is not None:
            total_restocked_qty += qty

        history_data.append({
            'id': log.id,
            'date': timezone.localtime(log.created_at).strftime('%Y-%m-%d %H:%M'),
            'user_name': log.user_name or 'النظام',
            'quantity': qty,
            'changes': log.changes,
            'reason': log.reason or 'توريد كمية جديدة للمخزون',
        })

    return JsonResponse({
        'product_id': product.id,
        'product_name': product.name,
        'created_at': timezone.localtime(product.created_at).strftime('%Y-%m-%d %H:%M'),
        'initial_count': product.initial_count,
        'available_count': product.available_count,
        'total_restocked_qty': total_restocked_qty,
        'history': history_data,
    })


@login_required_custom
def delete_product_view(request, product_id):
    user = Users.objects.filter(id=request.session['user_id']).first()
    if not user:
        return redirect('login')

    sales_perm = user.get_tab_permission_level('sales')
    if sales_perm != 'all' or not user.can_edit_products():
        messages.error(request, 'ليس لديك صلاحية حذف المنتجات.')
        return redirect('/portal/?tab=sales')

    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product_name = product.name
        # Prevent deletion if the product has bill items
        if product.bill_items.exists():
            messages.error(
                request,
                f'تعذر حذف المنتج "{product_name}" لوجود فواتير بيع سابقة مسجلة به. يمكنك بدلاً من ذلك إيقاف تفعيل المنتج من خيار (إيقاف المنتج) لإيقاف بيعه مع الحفاظ على سجل الفواتير.'
            )
            return redirect('/portal/?tab=sales')

        try:
            # Dissociate from audit logs so logs remain for reference
            ProductAuditLog.objects.filter(product=product).update(product=None)

            # Record audit log for deletion
            ProductAuditLog.objects.create(
                product=None,
                product_name=product_name,
                action_type='edit',
                user=user,
                user_name=user.full_name,
                changes="حذف المنتج نهائياً من النظام",
                reason=request.POST.get('delete_reason', '').strip() or "حذف المنتج بواسطة المستخدم",
            )
            product.delete()
            messages.success(request, f'تم حذف المنتج "{product_name}" بنجاح من النظام.')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء محاولة حذف المنتج: {str(e)}')

    return redirect('/portal/?tab=sales')


@login_required_custom
def bill_detail_json_view(request, bill_id):
    """Return JSON details for print and modal viewer."""
    user = Users.objects.filter(id=request.session['user_id']).first()
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    bill = get_object_or_404(Bill.objects.select_related('client', 'created_by', 'original_bill').prefetch_related('items'), id=bill_id)
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
        'bill_number': bill.bill_number or str(bill.id),
        'original_bill_number': (bill.original_bill.bill_number or str(bill.original_bill.id)) if bill.original_bill else None,
        'bill_type': bill.bill_type,
        'bill_type_display': bill.get_bill_type_display(),
        'created_at': timezone.localtime(bill.created_at).strftime('%Y-%m-%d %H:%M'),
        'client_name': bill.client.name,
        'client_phone': bill.client.phone,
        'network_name': bill.client.network_name or '—',
        'created_by': bill.created_by.full_name if bill.created_by else 'النظام',
        'total_amount': float(bill.total_amount),
        'notes': bill.notes or '',
        'items': items_data,
    })


@login_required_custom
def lookup_bill_json_view(request):
    """API to lookup a sales bill by number/ID for refund matching."""
    user = Users.objects.filter(id=request.session['user_id']).first()
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    raw_query = request.GET.get('number', '').strip()
    clean_query = raw_query.lstrip('#').strip()
    if not clean_query:
        return JsonResponse({'found': False, 'error': 'يرجى إدخال رقم الفاتورة.'})

    q = Q(bill_type='sales') & (Q(bill_number=clean_query) | Q(bill_number__iexact=clean_query))
    if clean_query.isdigit():
        q |= (Q(bill_type='sales') & Q(id=int(clean_query)))

    bill = Bill.objects.filter(q).select_related('client').prefetch_related('items__product').first()
    if not bill:
        return JsonResponse({
            'found': False,
            'error': f'لم يتم العثور على فاتورة مبيعات بالرقم "{clean_query}". يرجى التحقق من الرقم.'
        })

    items_data = []
    for item in bill.items.all():
        if item.product:
            already_refunded = BillItem.objects.filter(
                bill__original_bill=bill,
                bill__bill_type='refund',
                product=item.product
            ).aggregate(Sum('quantity'))['quantity__sum'] or 0

            # Warehouse net sold check
            total_sales = item.product.bill_items.filter(bill__bill_type='sales').aggregate(Sum('quantity'))['quantity__sum'] or 0
            total_refund = item.product.bill_items.filter(bill__bill_type='refund').aggregate(Sum('quantity'))['quantity__sum'] or 0
            warehouse_net = max(0, total_sales - total_refund)
        else:
            already_refunded = 0
            warehouse_net = item.quantity

        remaining_refundable = max(0, item.quantity - already_refunded)
        max_refundable = min(remaining_refundable, warehouse_net)

        items_data.append({
            'product_id': item.product_id,
            'product_name': item.product_name,
            'purchased_quantity': item.quantity,
            'already_refunded': already_refunded,
            'remaining_refundable': remaining_refundable,
            'max_refundable': max_refundable,
            'price': float(item.price),
            'condition': item.get_condition_display(),
        })

    return JsonResponse({
        'found': True,
        'bill_id': bill.id,
        'bill_number': bill.bill_number or str(bill.id),
        'created_at': timezone.localtime(bill.created_at).strftime('%Y-%m-%d %H:%M'),
        'client_name': bill.client.name,
        'client_phone': bill.client.phone,
        'client_network': bill.client.network_name or '',
        'total_amount': float(bill.total_amount),
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
    can_create_refund_bill = user.is_superuser or (sales_perm == 'all') or (services_perm == 'all') or (bills_perm == 'all')

    if not can_create_sales_bill and not can_create_services_bill and not can_create_refund_bill:
        messages.error(request, 'ليس لديك صلاحية لإنشاء الفواتير.')
        return redirect('portal')

    if request.method == 'POST':
        bill_type = request.POST.get('bill_type', 'sales')  # 'sales', 'services', or 'refund'

        if bill_type == 'sales' and not can_create_sales_bill:
            messages.error(request, 'ليس لديك صلاحية لإنشاء فواتير المبيعات أو أن قسم المنتجات مقفل.')
            return redirect('portal')

        if bill_type == 'services' and not can_create_services_bill:
            messages.error(request, 'ليس لديك صلاحية لإنشاء فواتير الخدمات أو أن قسم الخدمات مقفل.')
            return redirect('portal')

        if bill_type == 'refund' and not can_create_refund_bill:
            messages.error(request, 'ليس لديك صلاحية لإنشاء فواتير المرتجع.')
            return redirect('portal')

        client = None
        if bill_type != 'refund':
            client_name = request.POST.get('client_name', '').strip()
            client_phone = request.POST.get('client_phone', '').strip()
            network_name = request.POST.get('network_name', '').strip()

            if not client_name or not client_phone:
                messages.error(request, 'يرجى إدخال اسم العميل ورقم هاتفه.')
                return redirect(request.META.get('HTTP_REFERER', f'/portal/?tab={bill_type}'))

        with transaction.atomic():
            if bill_type != 'refund':
                # Get or create client for sales / services
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
                    bill_type='services',
                    total_amount=service_cost,
                    notes=f"خدمة: {service_description}",
                )

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

            elif bill_type == 'refund':
                # Refund bill
                orig_number = request.POST.get('original_bill_number', '').strip().lstrip('#').strip()
                product_id = request.POST.get('refund_product_id') or request.POST.get('product_id')
                quantity_str = request.POST.get('refund_quantity') or request.POST.get('quantity', '1')
                refund_reason = request.POST.get('refund_reason', '').strip()

                if not orig_number:
                    messages.error(request, 'يرجى إدخال رقم فاتورة الشراء الأصلية للتحقق والمطابقة.')
                    return redirect('/portal/?tab=bills')

                q_orig = Q(bill_type='sales') & (Q(bill_number=orig_number) | Q(bill_number__iexact=orig_number))
                if orig_number.isdigit():
                    q_orig |= (Q(bill_type='sales') & Q(id=int(orig_number)))

                original_bill = Bill.objects.filter(q_orig).select_related('client').prefetch_related('items__product').first()
                if not original_bill:
                    messages.error(request, f'رقم فاتورة الشراء "{orig_number}" غير موجود أو أنها ليست فاتورة مبيعات مؤكدة.')
                    return redirect('/portal/?tab=bills')

                if not product_id:
                    messages.error(request, 'يرجى اختيار المنتج المرتجع.')
                    return redirect('/portal/?tab=bills')

                product = Product.objects.filter(id=product_id).first()
                if not product:
                    messages.error(request, 'المنتج المحدد غير موجود.')
                    return redirect('/portal/?tab=bills')

                # Verify product was in original bill
                orig_item = original_bill.items.filter(product=product).first()
                if not orig_item:
                    messages.error(
                        request,
                        f'المنتج "{product.name}" لم يتم شراؤه في فاتورة المبيعات رقم #{original_bill.bill_number or original_bill.id}.'
                    )
                    return redirect('/portal/?tab=bills')

                try:
                    quantity = int(quantity_str)
                    if quantity <= 0:
                        quantity = 1
                except ValueError:
                    quantity = 1

                # Calculate already refunded quantity for this product from this specific original bill
                already_refunded = BillItem.objects.filter(
                    bill__original_bill=original_bill,
                    bill__bill_type='refund',
                    product=product
                ).aggregate(Sum('quantity'))['quantity__sum'] or 0

                remaining_from_bill = orig_item.quantity - already_refunded
                if remaining_from_bill <= 0:
                    messages.error(
                        request,
                        f'تم استرجاع كامل الكمية المشتراة من المنتج "{product.name}" ({orig_item.quantity} قطع) في هذه الفاتورة سابقاً.'
                    )
                    return redirect('/portal/?tab=bills')

                if quantity > remaining_from_bill:
                    messages.error(
                        request,
                        f'الكمية المراد استرجاعها ({quantity} قطع) أكبر من الكمية المتبقية القابلة للإرجاع من هذه الفاتورة ({remaining_from_bill} قطع).'
                    )
                    return redirect('/portal/?tab=bills')

                # Store-wide net sold check
                total_sales_sold = product.bill_items.filter(bill__bill_type='sales').aggregate(Sum('quantity'))['quantity__sum'] or 0
                total_refunded = product.bill_items.filter(bill__bill_type='refund').aggregate(Sum('quantity'))['quantity__sum'] or 0
                current_net_sold = max(0, total_sales_sold - total_refunded)
                if quantity > current_net_sold:
                    messages.error(
                        request,
                        f'لا يمكن إرجاع ({quantity}) قطع لأن إجمالي المبيعات المتبقية في المخزن لهذا المنتج ({current_net_sold}) قطع فقط.'
                    )
                    return redirect('/portal/?tab=bills')

                item_price = orig_item.price
                refund_amount = Decimal(item_price) * Decimal(quantity)

                bill = Bill.objects.create(
                    client=original_bill.client,
                    created_by=user,
                    bill_type='refund',
                    original_bill=original_bill,
                    total_amount=refund_amount,
                    notes=f"فاتورة مرتجع لفاتورة الشراء #{original_bill.bill_number or original_bill.id}: {refund_reason or 'استرجاع بضاعة'}",
                )

                BillItem.objects.create(
                    bill=bill,
                    product=product,
                    product_name=f"[مرتجع] {product.name}",
                    price=item_price,
                    condition=orig_item.condition,
                    quantity=quantity,
                )

                # Record audit log for refund
                ProductAuditLog.objects.create(
                    product=product,
                    product_name=product.name,
                    action_type='refund',
                    user=user,
                    user_name=user.full_name,
                    changes=f"فاتورة مرتجع #{bill.bill_number or bill.id} تابعة لفاتورة الشراء #{original_bill.bill_number or original_bill.id}: تم استرجاع {quantity} قطعة من العميل '{original_bill.client.name}' إلى المخزن (المتوفر حالياً: {product.available_count} قطعة | المبلغ المسترد: {refund_amount} ر.ي)",
                    reason=refund_reason or f"استرجاع بضاعة من فاتورة #{original_bill.bill_number or original_bill.id}",
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

                if not product.is_active:
                    messages.error(request, f'المنتج "{product.name}" موقوف حالياً عن البيع ولا يمكن إنشاء فاتورة له.')
                    return redirect(request.META.get('HTTP_REFERER', '/portal/?tab=sales'))

                if product.available_count <= 0:
                    messages.error(request, f'المنتج "{product.name}" غير متوفر (نفدت الكمية). لا يمكن إنشاء فاتورة له.')
                    return redirect(request.META.get('HTTP_REFERER', '/portal/?tab=sales'))

                if product.available_count < quantity:
                    messages.error(request, f'الكمية المتوفرة من "{product.name}" ({product.available_count}) غير كافية لطلب كمية ({quantity}).')
                    return redirect(request.META.get('HTTP_REFERER', '/portal/?tab=sales'))

                bill = Bill.objects.create(
                    client=client,
                    created_by=user,
                    bill_type='sales',
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

        if bill_type == 'refund':
            messages.success(request, f'تم إنشاء فاتورة المرتجع رقم #{bill.bill_number or bill.id} والمطابقة مع الفاتورة #{original_bill.bill_number or original_bill.id} وإعادة {quantity} قطعة للمخزن بنجاح.')
        else:
            messages.success(request, f'تم إنشاء الفاتورة رقم #{bill.bill_number or bill.id} للعميل "{client.name}" بنجاح.')
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

from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('portal/', views.dashboard_view, name='portal'),
    path('dashboard/', views.dashboard_redirect, name='dashboard'),  # backwards compatibility redirect to portal
    path('portal/add-product/', views.add_product_view, name='add_product'),
    path('portal/edit-product/<int:product_id>/', views.edit_product_view, name='edit_product'),
    path('portal/delete-product/<int:product_id>/', views.delete_product_view, name='delete_product'),
    path('portal/bill-json/<int:bill_id>/', views.bill_detail_json_view, name='bill_detail_json'),
    path('portal/create-bill/', views.create_bill_view, name='create_bill'),
    path('admin-permissions/', views.admin_permissions_view, name='admin_permissions'),
    path('admin-permissions/add-user/', views.add_user_view, name='add_user'),
    path('update-permissions/', views.update_permissions_view, name='update_permissions'),
]

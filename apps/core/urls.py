from django.urls import path
from . import views
from . import admin_views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('scan/', views.scan_view, name='scan'),
    path('dine-in/', views.scan_view, name='dine_in'),

    # Admin Panel routes
    path('admin-panel/', admin_views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-panel/orders/', admin_views.admin_orders_list_view, name='admin_orders'),
    path('admin-panel/orders/<uuid:order_id>/assign/', admin_views.admin_manual_assign_partner, name='admin_manual_assign'),
    path('admin-panel/orders/<uuid:order_id>/status/', admin_views.admin_change_order_status, name='admin_change_status'),
    path('admin-panel/users/', admin_views.admin_users_list_view, name='admin_users'),
    path('admin-panel/users/<uuid:user_id>/toggle/', admin_views.admin_toggle_user_status, name='admin_toggle_user'),
    path('admin-panel/reports/', admin_views.admin_reports_view, name='admin_reports'),
    path('admin-panel/reports/export-csv/', admin_views.admin_export_csv_view, name='admin_export_csv'),
]


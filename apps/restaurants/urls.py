from django.urls import path
from . import views

app_name = 'restaurants'

urlpatterns = [
    path('', views.RestaurantListView.as_view(), name='list'),
    path('<slug:slug>/', views.RestaurantDetailView.as_view(), name='detail'),
    path('api/items/<uuid:item_id>/toggle-stock/', views.ToggleMenuItemStockAPI.as_view(), name='toggle_stock'),
]


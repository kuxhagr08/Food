from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

app_name = 'accounts'

urlpatterns = [
    path('redirect/', views.RoleBasedRedirectView.as_view(), name='redirect'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.custom_logout, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('address/add/', views.address_create_view, name='address_create'),
    path('address/<uuid:address_id>/delete/', views.address_delete_view, name='address_delete'),
    path('address/<uuid:address_id>/default/', views.address_set_default_view, name='address_default'),

    # API Endpoints
    path('api/me/', views.CurrentUserAPIView.as_view(), name='api_me'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]


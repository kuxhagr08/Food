from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.generic import View, CreateView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from .forms import LoginForm, RegisterForm, AddressForm
from .models import User, Address

class RoleBasedRedirectView(View):
    """Redirects authenticated users to their specific dashboard based on their role."""
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        next_url = request.GET.get('next')
        if next_url and next_url != '/accounts/redirect/':
            return redirect(next_url)

        role = getattr(request.user, 'role', 'customer')
        if role == 'admin' or request.user.is_superuser:
            return redirect('/admin-panel/')
        elif role == 'kitchen_staff':
            return redirect('/kitchen/dashboard/')
        elif role == 'delivery_partner':
            return redirect('/delivery/dashboard/')
        else:
            return redirect('/')


def merge_anonymous_cart_into_user_cart(old_session_key, user):
    """Transfers all items from anonymous session cart into the authenticated user cart."""
    if not old_session_key:
        return
    try:
        from apps.orders.models import Cart, CartItem
        anon_cart = Cart.objects.filter(session_key=old_session_key, user__isnull=True).first()
        if not anon_cart or not anon_cart.items.exists():
            return

        user_cart, _ = Cart.objects.get_or_create(user=user)
        if not user_cart.restaurant:
            user_cart.restaurant = anon_cart.restaurant
            user_cart.applied_coupon = anon_cart.applied_coupon
            user_cart.save()

        if user_cart.restaurant == anon_cart.restaurant:
            for item in anon_cart.items.all():
                existing = user_cart.items.filter(menu_item=item.menu_item).first()
                if existing:
                    existing.quantity += item.quantity
                    existing.save()
                else:
                    item.cart = user_cart
                    item.save()

        anon_cart.items.all().delete()
        anon_cart.delete()
    except Exception as e:
        print("Cart merge error:", e)


class CustomLoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        next_url = request.GET.get('next', '')
        if request.user.is_authenticated:
            if next_url and next_url != '/accounts/redirect/':
                return redirect(next_url)
            return redirect('accounts:redirect')
        form = LoginForm()
        return render(request, self.template_name, {'form': form, 'next': next_url})

    def post(self, request):
        old_session_key = request.session.session_key
        form = LoginForm(request, data=request.POST)
        next_url = request.POST.get('next') or request.GET.get('next') or ''

        if form.is_valid():
            user = form.get_user()
            user.backend = 'apps.accounts.backends.EmailOrUsernameModelBackend'
            login(request, user, backend='apps.accounts.backends.EmailOrUsernameModelBackend')
            merge_anonymous_cart_into_user_cart(old_session_key, user)
            messages.success(request, f"Welcome back, {user.first_name or user.email}!")
            if next_url and next_url != '/accounts/redirect/':
                return redirect(next_url)
            return redirect('accounts:redirect')
        else:
            messages.error(request, "Invalid email/username or password.")
            return render(request, self.template_name, {'form': form, 'next': next_url})


class RegisterView(View):
    template_name = 'accounts/register.html'

    def get(self, request):
        next_url = request.GET.get('next', '')
        if request.user.is_authenticated:
            if next_url and next_url != '/accounts/redirect/':
                return redirect(next_url)
            return redirect('accounts:redirect')
        form = RegisterForm()
        return render(request, self.template_name, {'form': form, 'next': next_url})

    def post(self, request):
        old_session_key = request.session.session_key
        form = RegisterForm(request.POST)
        next_url = request.POST.get('next') or request.GET.get('next') or ''

        if form.is_valid():
            user = form.save()
            user.backend = 'apps.accounts.backends.EmailOrUsernameModelBackend'
            login(request, user, backend='apps.accounts.backends.EmailOrUsernameModelBackend')
            merge_anonymous_cart_into_user_cart(old_session_key, user)
            messages.success(request, f"Welcome to QuickBite, {user.first_name}!")
            if next_url and next_url != '/accounts/redirect/':
                return redirect(next_url)
            return redirect('/')
        else:
            return render(request, self.template_name, {'form': form, 'next': next_url})


def custom_logout(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('/')


@login_required
def profile_view(request):
    addresses = request.user.addresses.all().order_by('-is_default', '-created_at')
    address_form = AddressForm()
    
    if request.method == 'POST' and 'update_profile' in request.POST:
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        request.user.first_name = first_name
        request.user.last_name = last_name
        if phone:
            request.user.phone = phone
        request.user.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('accounts:profile')

    return render(request, 'accounts/profile.html', {
        'user': request.user,
        'addresses': addresses,
        'address_form': address_form,
    })


@login_required
def address_create_view(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            # If this is the user's only address, make it default
            if not request.user.addresses.exists():
                address.is_default = True
            address.save()
            messages.success(request, "Delivery address added.")
        else:
            messages.error(request, "Please check the address form inputs.")
    return redirect(request.META.get('HTTP_REFERER', 'accounts:profile'))


@login_required
def address_delete_view(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()
    messages.success(request, "Address removed.")
    return redirect(request.META.get('HTTP_REFERER', 'accounts:profile'))


@login_required
def address_set_default_view(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.is_default = True
    address.save()
    messages.success(request, f"'{address.title}' set as default address.")
    return redirect(request.META.get('HTTP_REFERER', 'accounts:profile'))


class CurrentUserAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': str(user.id),
            'email': user.email,
            'phone': user.phone,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'is_online': user.is_online,
            'current_lat': user.current_lat,
            'current_lng': user.current_lng,
        })


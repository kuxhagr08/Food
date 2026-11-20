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


class CustomLoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:redirect')
        form = LoginForm()
        return render(request, self.template_name, {'form': form, 'next': request.GET.get('next', '')})

    def post(self, request):
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.email}!")
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('accounts:redirect')
        else:
            messages.error(request, "Invalid email or password.")
            return render(request, self.template_name, {'form': form, 'next': request.POST.get('next', '')})


class RegisterView(View):
    template_name = 'accounts/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:redirect')
        form = RegisterForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful! Welcome to QuickBite.")
            return redirect('/')
        else:
            return render(request, self.template_name, {'form': form})


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


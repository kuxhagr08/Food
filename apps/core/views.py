from django.shortcuts import render
from apps.restaurants.models import Category, Restaurant, MenuItem
from apps.orders.models import Coupon

def home_view(request):
    categories = Category.objects.filter(is_active=True).order_by('sort_order')
    popular_restaurants = Restaurant.objects.filter(is_active=True).order_by('-rating')[:8]
    active_coupons = Coupon.objects.filter(is_active=True)[:4]
    
    # Spotlight bestsellers across restaurants
    bestseller_items = (
        MenuItem.objects.filter(is_available=True)
        .select_related('restaurant', 'category')
        .order_by('-restaurant__rating', 'price')[:8]
    )

    return render(request, 'customer/home.html', {
        'categories': categories,
        'popular_restaurants': popular_restaurants,
        'active_coupons': active_coupons,
        'bestseller_items': bestseller_items,
    })

def about_view(request):
    return render(request, 'customer/about.html')

def contact_view(request):
    return render(request, 'customer/contact.html')

def scan_view(request):
    restaurants = Restaurant.objects.filter(is_active=True).order_by('name')
    return render(request, 'customer/scan_dine_in.html', {
        'restaurants': restaurants,
    })


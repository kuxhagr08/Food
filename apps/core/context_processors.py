def site_settings(request):
    """
    Global context processor providing site-wide variables like cart item count,
    user role flags, and basic brand information.
    """
    context = {
        'SITE_NAME': 'QuickBite',
        'DEFAULT_CURRENCY': '₹',
        'is_customer': False,
        'is_admin': False,
        'is_kitchen': False,
        'is_delivery': False,
        'cart_count': 0,
    }
    
    if request.user.is_authenticated:
        role = getattr(request.user, 'role', 'customer')
        context['user_role'] = role
        context['is_customer'] = (role == 'customer')
        context['is_admin'] = (role == 'admin' or request.user.is_superuser)
        context['is_kitchen'] = (role == 'kitchen_staff')
        context['is_delivery'] = (role == 'delivery_partner')

        # Get cart count
        try:
            from apps.orders.models import Cart
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                context['cart_count'] = cart.items.count()
        except Exception:
            context['cart_count'] = 0
    else:
        # Check session cart
        session_cart = request.session.get('cart', {})
        context['cart_count'] = sum(session_cart.values()) if session_cart else 0

    return context


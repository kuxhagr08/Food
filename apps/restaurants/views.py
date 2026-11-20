from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, View
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from .models import Category, Restaurant, MenuItem

class RestaurantListView(ListView):
    model = Restaurant
    template_name = 'customer/restaurant_list.html'
    context_object_name = 'restaurants'
    paginate_by = 12

    def get_queryset(self):
        qs = Restaurant.objects.filter(is_active=True)
        search_query = self.request.GET.get('q', '').strip()
        category_slug = self.request.GET.get('category', '').strip()
        veg_only = self.request.GET.get('veg', '') == '1'
        sort_by = self.request.GET.get('sort', 'rating')

        if search_query:
            qs = qs.filter(
                Q(name__icontains=search_query) |
                Q(menu_items__name__icontains=search_query) |
                Q(menu_items__category__name__icontains=search_query)
            ).distinct()

        if category_slug:
            qs = qs.filter(menu_items__category__slug=category_slug).distinct()

        if veg_only:
            qs = qs.filter(menu_items__is_veg=True).distinct()

        if sort_by == 'rating':
            qs = qs.order_by('-rating')
        elif sort_by == 'time':
            qs = qs.order_by('avg_prep_time_mins')
        elif sort_by == 'min_order':
            qs = qs.order_by('min_order_amount')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True).order_by('sort_order')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_sort'] = self.request.GET.get('sort', 'rating')
        context['veg_only'] = self.request.GET.get('veg', '') == '1'
        context['search_query'] = self.request.GET.get('q', '')
        return context


class RestaurantDetailView(DetailView):
    model = Restaurant
    template_name = 'customer/restaurant_detail.html'
    context_object_name = 'restaurant'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        restaurant = self.object
        items = restaurant.menu_items.select_related('category').order_by('category__sort_order', 'name')

        table_no = self.request.GET.get('table')
        if table_no:
            self.request.session['dine_in_table'] = table_no
            context['table_number'] = table_no
            context['is_dine_in'] = True
        else:
            context['table_number'] = self.request.session.get('dine_in_table')
            context['is_dine_in'] = bool(context['table_number'])

        # Group items by category
        grouped_menu = {}
        for item in items:
            cat_name = item.category.name if item.category else 'Specialties'
            if cat_name not in grouped_menu:
                grouped_menu[cat_name] = []
            grouped_menu[cat_name].append(item)

        context['grouped_menu'] = grouped_menu
        return context


class ToggleMenuItemStockAPI(APIView):
    """Allows kitchen staff and admin to toggle an item's in-stock status."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, item_id):
        if request.user.role not in ['kitchen_staff', 'admin'] and not request.user.is_superuser:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        item = get_object_or_404(MenuItem, id=item_id)
        item.is_available = not item.is_available
        item.save(update_fields=['is_available'])

        return Response({
            'success': True,
            'item_id': str(item.id),
            'name': item.name,
            'is_available': item.is_available
        })


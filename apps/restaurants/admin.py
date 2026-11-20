from django.contrib import admin
from .models import Category, Restaurant, MenuItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1
    fields = ('name', 'category', 'price', 'discount_price', 'is_veg', 'is_available')

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'rating', 'total_ratings', 'avg_prep_time_mins', 'min_order_amount', 'is_active', 'is_accepting_orders')
    list_filter = ('is_active', 'is_accepting_orders')
    search_fields = ('name', 'address', 'phone')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [MenuItemInline]

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'category', 'price', 'discount_price', 'is_veg', 'is_available')
    list_filter = ('restaurant', 'category', 'is_veg', 'is_available')
    search_fields = ('name', 'restaurant__name')


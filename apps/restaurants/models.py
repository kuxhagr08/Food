import uuid
from django.db import models
from django.utils.text import slugify
from django.conf import settings
from apps.core.models import BaseModel

class Category(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji or icon class, e.g. 🍔, 🍕")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        slug = self.slug or slugify(self.name)
        images = {
            'burgers': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=400&q=80',
            'pizzas': 'https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=400&q=80',
            'biryani': 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=400&q=80',
            'chinese-momos': 'https://images.unsplash.com/photo-1541696432-82c6da8ce7bf?auto=format&fit=crop&w=400&q=80',
            'north-south-indian': 'https://images.unsplash.com/photo-1589302168068-964664d93dc0?auto=format&fit=crop&w=400&q=80',
            'desserts-drinks': 'https://images.unsplash.com/photo-1551024709-8f23befc6f87?auto=format&fit=crop&w=400&q=80',
        }
        return images.get(slug, 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=400&q=80')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Restaurant(BaseModel):
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='restaurants')
    address = models.TextField()
    phone = models.CharField(max_length=20)
    latitude = models.FloatField(default=28.6139) # default New Delhi area
    longitude = models.FloatField(default=77.2090)
    logo = models.ImageField(upload_to='restaurants/logos/', null=True, blank=True)
    banner = models.ImageField(upload_to='restaurants/banners/', null=True, blank=True)
    rating = models.FloatField(default=4.5, db_index=True)
    total_ratings = models.PositiveIntegerField(default=120)
    avg_prep_time_mins = models.PositiveIntegerField(default=25)
    min_order_amount = models.DecimalField(max_digits=8, decimal_places=2, default=99.00)
    is_active = models.BooleanField(default=True, db_index=True)
    is_accepting_orders = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Restaurant'
        verbose_name_plural = 'Restaurants'
        ordering = ['-rating', 'name']

    def __str__(self):
        return self.name

    @property
    def display_banner(self):
        if self.banner:
            return self.banner.url
        slug = self.slug or slugify(self.name)
        banners = {
            'burger-crave': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=800&q=80',
            'pizza-pronto': 'https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=800&q=80',
            'spice-symphony': 'https://images.unsplash.com/photo-1589302168068-964664d93dc0?auto=format&fit=crop&w=800&q=80',
            'dragon-wok': 'https://images.unsplash.com/photo-1541696432-82c6da8ce7bf?auto=format&fit=crop&w=800&q=80',
            'sweet-treat-cafe': 'https://images.unsplash.com/photo-1551024709-8f23befc6f87?auto=format&fit=crop&w=800&q=80',
        }
        return banners.get(slug, 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=800&q=80')

    @property
    def cuisines_list(self):
        slug = self.slug or slugify(self.name)
        data = {
            'burger-crave': 'Burgers, American, Crispy Fries, Shakes',
            'pizza-pronto': 'Woodfired Pizzas, Pastas, Garlic Bread',
            'spice-symphony': 'Hyderabadi Biryani, Mughlai, Kebabs',
            'dragon-wok': 'Chinese, Dim Sums, Hakka Noodles, Momos',
            'sweet-treat-cafe': 'Artisan Bakery, Desserts, Cold Coffee',
        }
        return data.get(slug, 'Fast Food, Multi-cuisine, Beverages')

    @property
    def offer_tag(self):
        slug = self.slug or slugify(self.name)
        offers = {
            'burger-crave': '60% OFF UP TO ₹120',
            'pizza-pronto': '50% OFF UP TO ₹100',
            'spice-symphony': 'FLAT ₹150 OFF',
            'dragon-wok': '40% OFF UP TO ₹80',
            'sweet-treat-cafe': 'BUY 1 GET 1 FREE',
        }
        return offers.get(slug, '20% OFF TODAY')

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Restaurant.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class MenuItem(BaseModel):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='menu_items')
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    discount_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    is_veg = models.BooleanField(default=True, db_index=True)
    is_available = models.BooleanField(default=True, db_index=True)
    image = models.ImageField(upload_to='menu_items/', null=True, blank=True)

    class Meta:
        verbose_name = 'Menu Item'
        verbose_name_plural = 'Menu Items'
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} - ₹{self.price} ({self.restaurant.name})"

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        name_lower = self.name.lower()
        if 'burger' in name_lower:
            return 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=400&q=80'
        elif 'pizza' in name_lower:
            return 'https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=400&q=80'
        elif 'biryani' in name_lower or 'rice' in name_lower:
            return 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=400&q=80'
        elif 'noodle' in name_lower or 'chowmein' in name_lower:
            return 'https://images.unsplash.com/photo-1585032226651-759b368d7246?auto=format&fit=crop&w=400&q=80'
        elif 'momo' in name_lower or 'dimsum' in name_lower:
            return 'https://images.unsplash.com/photo-1625246333195-78d9c38ad449?auto=format&fit=crop&w=400&q=80'
        elif 'paneer' in name_lower or 'tikka' in name_lower or 'curry' in name_lower:
            return 'https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=400&q=80'
        elif 'coffee' in name_lower or 'shake' in name_lower or 'drink' in name_lower:
            return 'https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=400&q=80'
        elif 'cake' in name_lower or 'brownie' in name_lower or 'pastry' in name_lower or 'dessert' in name_lower:
            return 'https://images.unsplash.com/photo-1587314168485-3236d6710814?auto=format&fit=crop&w=400&q=80'
        return 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=400&q=80'

    @property
    def effective_price(self):
        if self.discount_price and self.discount_price > 0 and self.discount_price < self.price:
            return self.discount_price
        return self.price


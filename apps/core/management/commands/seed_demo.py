from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.accounts.models import Address
from apps.restaurants.models import Restaurant, Category, MenuItem
from apps.orders.models import Coupon, Order, OrderItem, OrderStatusHistory
from apps.delivery.models import DeliveryAssignment
from apps.cms.models import CMSPage, CMSPageVersion

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds complete demo data for QuickBite food delivery platform (Idempotent)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("--- Seeding QuickBite Platform Demo Data ---"))

        # 1. Users
        users_data = [
            # Admins
            {'email': 'admin@quickbite.com', 'password': 'admin123', 'first_name': 'Kushagra', 'last_name': 'Admin', 'role': 'admin', 'is_staff': True, 'is_superuser': True},
            # Kitchen Staff
            {'email': 'kitchen1@quickbite.com', 'password': 'kitchen123', 'first_name': 'Chef', 'last_name': 'Sanjay', 'role': 'kitchen_staff', 'is_staff': False},
            {'email': 'kitchen2@quickbite.com', 'password': 'kitchen123', 'first_name': 'Chef', 'last_name': 'Anita', 'role': 'kitchen_staff', 'is_staff': False},
            # Delivery Partners
            {'email': 'partner1@quickbite.com', 'password': 'partner123', 'first_name': 'Ramesh', 'last_name': 'Kumar', 'role': 'delivery_partner', 'phone': '+919876543201', 'is_online': True, 'lat': 28.6145, 'lng': 77.2085},
            {'email': 'partner2@quickbite.com', 'password': 'partner123', 'first_name': 'Vikram', 'last_name': 'Singh', 'role': 'delivery_partner', 'phone': '+919876543202', 'is_online': True, 'lat': 28.6200, 'lng': 77.2150},
            {'email': 'partner3@quickbite.com', 'password': 'partner123', 'first_name': 'Sunil', 'last_name': 'Sharma', 'role': 'delivery_partner', 'phone': '+919876543203', 'is_online': False, 'lat': 28.6100, 'lng': 77.2000},
            # Customers
            {'email': 'rahul@example.com', 'password': 'customer123', 'first_name': 'Rahul', 'last_name': 'Mehta', 'role': 'customer', 'phone': '+919811122233'},
            {'email': 'priya@example.com', 'password': 'customer123', 'first_name': 'Priya', 'last_name': 'Verma', 'role': 'customer', 'phone': '+919822233344'},
            {'email': 'amit@example.com', 'password': 'customer123', 'first_name': 'Amit', 'last_name': 'Patel', 'role': 'customer', 'phone': '+919833344455'},
        ]

        created_users = {}
        for u in users_data:
            user, created = User.objects.get_or_create(email=u['email'], defaults={
                'first_name': u['first_name'],
                'last_name': u['last_name'],
                'role': u['role'],
                'phone': u.get('phone'),
                'is_staff': u.get('is_staff', False),
                'is_superuser': u.get('is_superuser', False),
                'is_online': u.get('is_online', False),
                'current_lat': u.get('lat', 28.6139),
                'current_lng': u.get('lng', 77.2090),
            })
            if created or not user.check_password(u['password']):
                user.set_password(u['password'])
                user.save()
            created_users[u['email']] = user

        self.stdout.write(self.style.SUCCESS("✓ Users seeded successfully."))

        # 2. Customer Addresses
        customer_addresses = [
            {'user': created_users['rahul@example.com'], 'title': 'Home', 'line1': 'Flat 402, Lotus Towers, Connaught Place', 'city': 'New Delhi', 'pin': '110001', 'lat': 28.6315, 'lng': 77.2167},
            {'user': created_users['rahul@example.com'], 'title': 'Work', 'line1': 'Tech Park, Barakhamba Road', 'city': 'New Delhi', 'pin': '110001', 'lat': 28.6280, 'lng': 77.2250},
            {'user': created_users['priya@example.com'], 'title': 'Home', 'line1': 'B-12, Defence Colony', 'city': 'New Delhi', 'pin': '110024', 'lat': 28.5729, 'lng': 77.2323},
            {'user': created_users['amit@example.com'], 'title': 'Home', 'line1': 'C-89, Hauz Khas Enclave', 'city': 'New Delhi', 'pin': '110016', 'lat': 28.5494, 'lng': 77.2001},
        ]
        for a in customer_addresses:
            Address.objects.get_or_create(
                user=a['user'],
                title=a['title'],
                defaults={
                    'address_line1': a['line1'],
                    'city': a['city'],
                    'pincode': a['pin'],
                    'latitude': a['lat'],
                    'longitude': a['lng'],
                    'is_default': True,
                }
            )

        # 3. Categories
        categories_data = [
            {'name': 'Burgers', 'icon': '🍔', 'sort': 1},
            {'name': 'Pizzas', 'icon': '🍕', 'sort': 2},
            {'name': 'Biryani', 'icon': '🍛', 'sort': 3},
            {'name': 'Chinese & Momos', 'icon': '🥢', 'sort': 4},
            {'name': 'North & South Indian', 'icon': '🥘', 'sort': 5},
            {'name': 'Desserts & Drinks', 'icon': '🍰', 'sort': 6},
        ]
        created_categories = {}
        for c in categories_data:
            cat, _ = Category.objects.get_or_create(
                name=c['name'],
                defaults={'icon': c['icon'], 'sort_order': c['sort'], 'is_active': True}
            )
            created_categories[c['name']] = cat

        # 4. Restaurants
        restaurants_data = [
            {
                'name': 'Burger Crave',
                'slug': 'burger-crave',
                'address': 'Shop 14, Inner Circle, Connaught Place, New Delhi',
                'phone': '+91 11 2341 5501',
                'lat': 28.6320,
                'lng': 77.2180,
                'rating': 4.6,
                'total_ratings': 340,
                'prep_time': 20,
                'min_order': Decimal('99.00'),
            },
            {
                'name': 'Pizza Pronto',
                'slug': 'pizza-pronto',
                'address': '22, Scindia House, Janpath, New Delhi',
                'phone': '+91 11 2341 8802',
                'lat': 28.6290,
                'lng': 77.2195,
                'rating': 4.7,
                'total_ratings': 520,
                'prep_time': 25,
                'min_order': Decimal('199.00'),
            },
            {
                'name': 'Spice Symphony',
                'slug': 'spice-symphony',
                'address': '55, Regal Building, Sansad Marg, New Delhi',
                'phone': '+91 11 2334 1122',
                'lat': 28.6275,
                'lng': 77.2140,
                'rating': 4.8,
                'total_ratings': 680,
                'prep_time': 30,
                'min_order': Decimal('149.00'),
            },
            {
                'name': 'Dragon Wok',
                'slug': 'dragon-wok',
                'address': 'B-7, Palika Bazar Arcade, New Delhi',
                'phone': '+91 11 2332 4455',
                'lat': 28.6305,
                'lng': 77.2170,
                'rating': 4.4,
                'total_ratings': 210,
                'prep_time': 20,
                'min_order': Decimal('129.00'),
            },
            {
                'name': 'Sweet Treat Cafe',
                'slug': 'sweet-treat-cafe',
                'address': '9, Kasturba Gandhi Marg, New Delhi',
                'phone': '+91 11 2371 9900',
                'lat': 28.6240,
                'lng': 77.2220,
                'rating': 4.9,
                'total_ratings': 410,
                'prep_time': 15,
                'min_order': Decimal('79.00'),
            },
        ]

        created_restaurants = {}
        for r in restaurants_data:
            rest, _ = Restaurant.objects.get_or_create(
                slug=r['slug'],
                defaults={
                    'name': r['name'],
                    'address': r['address'],
                    'phone': r['phone'],
                    'latitude': r['lat'],
                    'longitude': r['lng'],
                    'rating': r['rating'],
                    'total_ratings': r['total_ratings'],
                    'avg_prep_time_mins': r['prep_time'],
                    'min_order_amount': r['min_order'],
                    'is_active': True,
                    'is_accepting_orders': True,
                }
            )
            created_restaurants[r['name']] = rest

        self.stdout.write(self.style.SUCCESS("✓ Restaurants and Categories seeded."))

        # 5. 40+ Food Items
        items_dataset = [
            # Burger Crave
            (created_restaurants['Burger Crave'], created_categories['Burgers'], 'Classic Crispy Veg Burger', 'Crunchy vegetable patty with house garlic mayo and lettuce', Decimal('99.00'), None, True),
            (created_restaurants['Burger Crave'], created_categories['Burgers'], 'Fiery Paneer Crunch Burger', 'Spicy fried paneer patty loaded with chipotle sauce', Decimal('149.00'), Decimal('129.00'), True),
            (created_restaurants['Burger Crave'], created_categories['Burgers'], 'Double Cheese Smash Burger', 'Two melted cheddar slices over vegetable crisper', Decimal('169.00'), None, True),
            (created_restaurants['Burger Crave'], created_categories['Burgers'], 'Grilled Chicken Feast Burger', 'Juicy grilled chicken patty with caramelized onions', Decimal('199.00'), Decimal('179.00'), False),
            (created_restaurants['Burger Crave'], created_categories['Burgers'], 'Crispy Bacon & Chicken Burger', 'Crispy chicken breast with smoky chicken bacon and mustard', Decimal('229.00'), None, False),
            (created_restaurants['Burger Crave'], created_categories['Desserts & Drinks'], 'Peri-Peri French Fries', 'Crisp potato fries dusted with piquant peri-peri seasoning', Decimal('89.00'), None, True),
            (created_restaurants['Burger Crave'], created_categories['Desserts & Drinks'], 'Belgian Chocolate Thick Shake', 'Rich cocoa ice cream shake topped with chocolate shavings', Decimal('139.00'), None, True),
            (created_restaurants['Burger Crave'], created_categories['Desserts & Drinks'], 'Iced Lemon Mint Cooler', 'Refreshing lemon fizz with muddled mint leaves', Decimal('79.00'), None, True),

            # Pizza Pronto
            (created_restaurants['Pizza Pronto'], created_categories['Pizzas'], 'Margherita Classica Pizza (8")', 'San Marzano tomato sauce, fresh mozzarella, and sweet basil', Decimal('219.00'), Decimal('199.00'), True),
            (created_restaurants['Pizza Pronto'], created_categories['Pizzas'], 'Farmhouse Veggie Overload (8")', 'Bell peppers, red onion, button mushrooms, and sweet corn', Decimal('269.00'), None, True),
            (created_restaurants['Pizza Pronto'], created_categories['Pizzas'], 'Paneer Tikka Fusion Pizza (8")', 'Tandoori paneer cubes, capsicum, and spiced tomato sauce', Decimal('289.00'), Decimal('259.00'), True),
            (created_restaurants['Pizza Pronto'], created_categories['Pizzas'], 'Chicken Pepperoni Delight (8")', 'Generously layered chicken pepperoni slices and gouda cheese', Decimal('349.00'), None, False),
            (created_restaurants['Pizza Pronto'], created_categories['Pizzas'], 'BBQ Smoked Chicken Pizza (8")', 'Tender chicken in sweet BBQ sauce with red paprika', Decimal('329.00'), Decimal('299.00'), False),
            (created_restaurants['Pizza Pronto'], created_categories['Pizzas'], 'Cheesy Garlic Breadsticks', 'Baked artisanal bread with roasted garlic butter and mozzarella', Decimal('129.00'), None, True),
            (created_restaurants['Pizza Pronto'], created_categories['Desserts & Drinks'], 'Choco Lava Volcano Cake', 'Warm molten chocolate cake with flowing gooey center', Decimal('99.00'), None, True),
            (created_restaurants['Pizza Pronto'], created_categories['Desserts & Drinks'], 'Classic Coke Can (330ml)', 'Chilled beverage can', Decimal('40.00'), None, True),

            # Spice Symphony
            (created_restaurants['Spice Symphony'], created_categories['Biryani'], 'Dum Pukht Veg Handi Biryani', 'Fragrant basmati rice layered with garden veggies and saffron', Decimal('249.00'), Decimal('229.00'), True),
            (created_restaurants['Spice Symphony'], created_categories['Biryani'], 'Hyderabadi Chicken Dum Biryani', 'Traditional clay pot biryani cooked with marinated succulent chicken', Decimal('299.00'), Decimal('279.00'), False),
            (created_restaurants['Spice Symphony'], created_categories['Biryani'], 'Mutton Royal Shahi Biryani', 'Slow-cooked tender tender goat meat with long-grain basmati and spices', Decimal('389.00'), None, False),
            (created_restaurants['Spice Symphony'], created_categories['North & South Indian'], 'Paneer Butter Masala', 'Soft cottage cheese cubes in velvety rich tomato cashew gravy', Decimal('239.00'), None, True),
            (created_restaurants['Spice Symphony'], created_categories['North & South Indian'], 'Dal Makhani Slow Simmered', 'Whole black lentils simmered overnight with butter and cream', Decimal('199.00'), None, True),
            (created_restaurants['Spice Symphony'], created_categories['North & South Indian'], 'Butter Chicken Aslam Style', 'Charcoal-grilled tandoori chicken cooked in creamy tomato butter glaze', Decimal('319.00'), Decimal('289.00'), False),
            (created_restaurants['Spice Symphony'], created_categories['North & South Indian'], 'Garlic Butter Naan', 'Tandoor-baked flatbread infused with minced garlic and butter', Decimal('49.00'), None, True),
            (created_restaurants['Spice Symphony'], created_categories['North & South Indian'], 'Crisp Masala Dosa', 'Golden fermented crepe filled with spiced potato mash and sambar', Decimal('139.00'), None, True),
            (created_restaurants['Spice Symphony'], created_categories['Desserts & Drinks'], 'Gulab Jamun (2 Pcs)', 'Warm khoya dumplings steeped in rose cardamom syrup', Decimal('79.00'), None, True),

            # Dragon Wok
            (created_restaurants['Dragon Wok'], created_categories['Chinese & Momos'], 'Steamed Veg Darjeeling Momos (6 Pcs)', 'Delicate dumplings filled with finely chopped cabbage, carrots and herbs', Decimal('119.00'), None, True),
            (created_restaurants['Dragon Wok'], created_categories['Chinese & Momos'], 'Kurkure Crunchy Paneer Momos (6 Pcs)', 'Crispy battered momos tossed in spicy peri-peri crumb', Decimal('149.00'), Decimal('129.00'), True),
            (created_restaurants['Dragon Wok'], created_categories['Chinese & Momos'], 'Juicy Steamed Chicken Momos (6 Pcs)', 'Minced chicken dumplings served with fiery red chili dip', Decimal('149.00'), None, False),
            (created_restaurants['Dragon Wok'], created_categories['Chinese & Momos'], 'Veg Hakka Noodles', 'Wok-tossed noodles with shredded bell peppers and scallions', Decimal('159.00'), None, True),
            (created_restaurants['Dragon Wok'], created_categories['Chinese & Momos'], 'Chilli Garlic Chicken Noodles', 'Spicy noodles with wok-fried chicken strips and roasted garlic', Decimal('199.00'), Decimal('179.00'), False),
            (created_restaurants['Dragon Wok'], created_categories['Chinese & Momos'], 'Crispy Chilli Paneer Dry', 'Indo-Chinese paneer cubes with green chilies and dark soy', Decimal('209.00'), None, True),
            (created_restaurants['Dragon Wok'], created_categories['Chinese & Momos'], 'Honey Chilli Potato Fingers', 'Crisp potato wedges glazed with sweet honey and sesame seeds', Decimal('149.00'), None, True),
            (created_restaurants['Dragon Wok'], created_categories['Chinese & Momos'], 'Chicken Manchurian Gravy', 'Tender chicken spheres simmered in tangy Manchurian sauce', Decimal('229.00'), None, False),

            # Sweet Treat Cafe
            (created_restaurants['Sweet Treat Cafe'], created_categories['Desserts & Drinks'], 'Fudge Brownie with Walnuts', 'Dense, dark chocolate brownie studded with roasted walnuts', Decimal('119.00'), Decimal('99.00'), True),
            (created_restaurants['Sweet Treat Cafe'], created_categories['Desserts & Drinks'], 'Red Velvet Cream Cheese Jar', 'Layers of red velvet sponge and fluffy cream cheese frosting', Decimal('149.00'), None, True),
            (created_restaurants['Sweet Treat Cafe'], created_categories['Desserts & Drinks'], 'New York Baked Cheesecake Slice', 'Classic silky Philadelphia style baked cheesecake', Decimal('179.00'), None, True),
            (created_restaurants['Sweet Treat Cafe'], created_categories['Desserts & Drinks'], 'Artisanal Cold Coffee Frappe', 'Rich blended espresso with chilled whole milk and vanilla gelato', Decimal('129.00'), None, True),
            (created_restaurants['Sweet Treat Cafe'], created_categories['Desserts & Drinks'], 'Mango Passion Smoothie', 'Real Alphonso mango pulp blended with Greek yogurt and honey', Decimal('139.00'), None, True),
            (created_restaurants['Sweet Treat Cafe'], created_categories['Desserts & Drinks'], 'Oreo Cookie Monster Shake', 'Thick crushed Oreo shake crowned with whipped cream', Decimal('149.00'), Decimal('129.00'), True),
            (created_restaurants['Sweet Treat Cafe'], created_categories['Desserts & Drinks'], 'Hazelnut Hot Chocolate', 'Steaming Belgian dark chocolate drink infused with hazelnut praline', Decimal('139.00'), None, True),
        ]

        item_count = 0
        for rest, cat, name, desc, price, disc_price, is_veg in items_dataset:
            item, created = MenuItem.objects.get_or_create(
                restaurant=rest,
                name=name,
                defaults={
                    'category': cat,
                    'description': desc,
                    'price': price,
                    'discount_price': disc_price,
                    'is_veg': is_veg,
                    'is_available': True,
                }
            )
            item_count += 1

        self.stdout.write(self.style.SUCCESS(f"✓ Seeded {item_count} Menu Items across all restaurants."))

        # 6. Coupons
        coupons = [
            {'code': 'WELCOME50', 'desc': '50% off up to ₹100 on your first orders', 'type': 'PERCENTAGE', 'val': Decimal('50.00'), 'min': Decimal('149.00'), 'max': Decimal('100.00')},
            {'code': 'FREEDEL', 'desc': 'Flat ₹30 off delivery fee on orders above ₹199', 'type': 'FLAT', 'val': Decimal('30.00'), 'min': Decimal('199.00'), 'max': None},
            {'code': 'TASTY20', 'desc': '20% discount on orders above ₹299', 'type': 'PERCENTAGE', 'val': Decimal('20.00'), 'min': Decimal('299.00'), 'max': Decimal('120.00')},
        ]
        for cp in coupons:
            Coupon.objects.get_or_create(
                code=cp['code'],
                defaults={
                    'description': cp['desc'],
                    'discount_type': cp['type'],
                    'discount_value': cp['val'],
                    'min_order_value': cp['min'],
                    'max_discount_amount': cp['max'],
                    'is_active': True,
                }
            )

        # 7. Sample Orders in Diverse Statuses
        customer_rahul = created_users['rahul@example.com']
        customer_priya = created_users['priya@example.com']
        partner_ramesh = created_users['partner1@quickbite.com']
        rest_burger = created_restaurants['Burger Crave']
        rest_spice = created_restaurants['Spice Symphony']

        sample_orders_data = [
            {
                'order_num': 'QB-880011',
                'customer': customer_rahul,
                'restaurant': rest_burger,
                'status': 'placed',
                'pay_method': 'COD',
                'pay_status': 'PENDING',
                'subtotal': Decimal('248.00'),
                'delivery_fee': Decimal('30.00'),
                'tax': Decimal('12.40'),
                'total': Decimal('290.40'),
                'partner': None,
            },
            {
                'order_num': 'QB-880022',
                'customer': customer_priya,
                'restaurant': rest_spice,
                'status': 'preparing',
                'pay_method': 'ONLINE',
                'pay_status': 'PAID',
                'subtotal': Decimal('438.00'),
                'delivery_fee': Decimal('40.00'),
                'tax': Decimal('21.90'),
                'total': Decimal('499.90'),
                'partner': partner_ramesh,
            },
            {
                'order_num': 'QB-880033',
                'customer': customer_rahul,
                'restaurant': rest_spice,
                'status': 'delivered',
                'pay_method': 'ONLINE',
                'pay_status': 'PAID',
                'subtotal': Decimal('548.00'),
                'delivery_fee': Decimal('30.00'),
                'tax': Decimal('27.40'),
                'total': Decimal('605.40'),
                'partner': partner_ramesh,
            },
        ]

        for so in sample_orders_data:
            order, o_created = Order.objects.get_or_create(
                order_number=so['order_num'],
                defaults={
                    'customer': so['customer'],
                    'restaurant': so['restaurant'],
                    'status': so['status'],
                    'payment_method': so['pay_method'],
                    'payment_status': so['pay_status'],
                    'subtotal': so['subtotal'],
                    'delivery_fee': so['delivery_fee'],
                    'tax_amount': so['tax'],
                    'discount_amount': Decimal('0.00'),
                    'total_amount': so['total'],
                    'delivery_address_title': 'Home',
                    'delivery_address_text': 'Flat 402, Lotus Towers, Connaught Place, New Delhi',
                    'delivery_lat': 28.6315,
                    'delivery_lng': 77.2167,
                    'pickup_otp': '1234',
                    'delivery_otp': '5678',
                    'delivery_partner': so['partner'],
                }
            )
            if o_created:
                # Add sample item
                first_item = so['restaurant'].menu_items.first()
                if first_item:
                    OrderItem.objects.create(
                        order=order,
                        menu_item=first_item,
                        item_name=first_item.name,
                        price=first_item.price,
                        quantity=2,
                        subtotal=first_item.price * 2
                    )
                OrderStatusHistory.objects.create(
                    order=order,
                    from_status='created',
                    to_status=so['status'],
                    changed_by_role='system',
                    notes='Seed sample order'
                )

        # 8. CMS Pages & Default Editable Blocks
        cms_pages_data = [
            {
                'title': 'Homepage Experience',
                'route': '/',
                'blocks': {
                    'hero_title': 'Craving something delicious? Delivered in 20 minutes.',
                    'hero_subtitle': 'Order from the top curated restaurants, cloud kitchens & cafes in your neighbourhood.',
                    'hero_cta_text': 'Explore Restaurants',
                    'offer_banner_text': 'Get 50% OFF up to ₹100 on your first order with coupon WELCOME50!',
                    'footer_about': 'QuickBite is India’s fastest real-time food delivery network. Fresh, hot, and transparently tracked.',
                    'footer_phone': '+91 1800 200 4545',
                    'footer_email': 'support@quickbite.com',
                }
            },
            {
                'title': 'About Us',
                'route': '/about/',
                'blocks': {
                    'page_title': 'About QuickBite',
                    'story_title': 'Built for Food Lovers & Lightning-Fast Deliveries',
                    'story_body': 'Founded in 2026, QuickBite bridges the distance between hungry food lovers and artisanal kitchen masters. Our hyper-local dispatch engine, integrated kitchen display systems (KDS), and live WebSocket routing ensure that every meal reaches your dining table piping hot.',
                }
            },
            {
                'title': 'Customer Support & Contact',
                'route': '/contact/',
                'blocks': {
                    'contact_heading': 'We are here to help you 24x7',
                    'contact_subheading': 'Have a question about an order, restaurant partnership, or delivery? Reach out anytime.',
                    'support_email': 'help@quickbite.com',
                    'support_phone': '+91 1800 200 4545',
                    'office_address': 'QuickBite HQ, Cyber City Tower B, Gurugram, India',
                }
            }
        ]

        for cp in cms_pages_data:
            page, p_created = CMSPage.objects.get_or_create(
                route=cp['route'],
                defaults={
                    'title': cp['title'],
                    'current_version': 1,
                    'is_published': True,
                    'updated_by': created_users['admin@quickbite.com'],
                }
            )
            if p_created:
                CMSPageVersion.objects.create(
                    page=page,
                    version_number=1,
                    content_blocks=cp['blocks'],
                    change_summary='Initial default release content',
                    created_by=created_users['admin@quickbite.com'],
                )

        self.stdout.write(self.style.SUCCESS("✓ Seeded CMS Pages (Home, About, Contact) with default editable blocks."))

        # Print Credentials Summary
        self.stdout.write(self.style.MIGRATE_LABEL("\n" + "="*70))
        self.stdout.write(self.style.SUCCESS(" QUICKBITE PLATFORM DEMO READY — LOGIN CREDENTIALS"))
        self.stdout.write(self.style.MIGRATE_LABEL("="*70))
        self.stdout.write(f"1. Admin Panel      : admin@quickbite.com     / admin123     -> /admin-panel/")
        self.stdout.write(f"2. Kitchen KDS      : kitchen1@quickbite.com  / kitchen123   -> /kitchen/dashboard/")
        self.stdout.write(f"3. Delivery Partner : partner1@quickbite.com  / partner123   -> /delivery/dashboard/")
        self.stdout.write(f"4. Customer Portal  : rahul@example.com       / customer123  -> /")
        self.stdout.write(f"5. Website Editor   : Accessible via Admin Panel -> /cms/pages/")
        self.stdout.write(self.style.MIGRATE_LABEL("="*70 + "\n"))


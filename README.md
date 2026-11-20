# QuickBite — Production-Grade Food Ordering & Delivery Platform (Zomato / Swiggy Style)

A complete, full-stack, real-time food ordering and delivery ecosystem built with **Python 3.12 / 3.14**, **Django 5.x LTS**, **Django Channels (WebSockets)**, **Redis**, **Celery**, and **Leaflet OpenStreetMap**.

---

## 1. Panels & Live URLs with Demo Logins

| Panel | Live Route | Demo Email | Demo Password | Role Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **Customer Web App** | [`/`](file:///Users/kushagrashrivastava/Desktop/MAJOR%20PROJECTS/food%20delivry/) | `rahul@example.com` | `customer123` | Browse menus, filters, cart, coupons, checkout, address map pin, live order tracking |
| **Kitchen Panel (KDS)** | [`/kitchen/dashboard/`](file:///Users/kushagrashrivastava/Desktop/MAJOR%20PROJECTS/food%20delivry/) | `kitchen1@quickbite.com` | `kitchen123` | 3-column Burger King KDS screen, sound alarm sirens, prep timers, item stock toggle |
| **Delivery Partner** | [`/delivery/dashboard/`](file:///Users/kushagrashrivastava/Desktop/MAJOR%20PROJECTS/food%20delivry/) | `partner1@quickbite.com` | `partner123` | Mobile-first, online/offline GPS watcher, Haversine nearby orders, route map, pickup/delivery OTPs |
| **Admin Control Center** | [`/admin-panel/`](file:///Users/kushagrashrivastava/Desktop/MAJOR%20PROJECTS/food%20delivry/) | `admin@quickbite.com` | `admin123` | Metrics, Chart.js trends, manual partner dispatch, block/activate users, reports & CSV export |
| **Website Visual Editor** | [`/cms/pages/`](file:///Users/kushagrashrivastava/Desktop/MAJOR%20PROJECTS/food%20delivry/) | `admin@quickbite.com` | `admin123` | Live preview with Desktop/Tablet/Mobile switch, inline click-to-edit, password save, versioning & rollback |

*Note: You can also use the one-click demo login buttons directly on the [`/accounts/login/`](file:///Users/kushagrashrivastava/Desktop/MAJOR%20PROJECTS/food%20delivry/) page to instantly autofill any role credentials.*

---

## 2. Architecture & Modules

```
food_delivery/
├── apps/
│   ├── core/                    # Base models, Haversine distance, RBAC permissions, Admin dashboard
│   ├── accounts/                # Custom User model (4 roles), Address pin locator, JWT & sessions
│   ├── restaurants/             # Categories, Restaurants, 40+ Food Items, Stock toggle APIs
│   ├── orders/                  # Order, Cart, Coupon, State Machine service, PriceCalculator
│   ├── delivery/                # Partner portal, GPS tracker, atomic acceptance (select_for_update), OTPs
│   ├── kitchen/                 # Full-screen KDS, Web Audio API alarm sirens, prep timers
│   ├── cms/                     # Dynamic Page models, Visual Editor, nh3 XSS sanitizer, version history & rollback
│   ├── payments/                # Razorpay test mode / mock payment gateway
│   └── notifications/           # Django Channels WebSockets consumers (Tracking, KDS, Delivery, Admin)
├── templates/                   # Clean HTML5 + CSS variables light-theme responsive layouts
├── static/                      # CSS design system, audio alerts engine, client JS
└── tests/                       # Complete pytest-django test suite
```

### Realtime Flow & State Machine
1. **Order Placed**: Customer places order $\rightarrow$ Server calculates exact price $\rightarrow$ broadcast to `kitchen_<restaurant_id>` with audio siren chime.
2. **Kitchen Accepts**: Staff selects prep time (10/15/20/30m) $\rightarrow$ Marks "Preparing" $\rightarrow$ Marks "Ready".
3. **Delivery Dispatch**: When marked "Ready", broadcasted to `delivery_partners` $\rightarrow$ Sorted by Haversine distance $\rightarrow$ Partner accepts using `select_for_update()` (concurrency-safe race protection).
4. **GPS Tracking**: Delivery partner shares live GPS location $\rightarrow$ Pushed via WebSocket directly to customer's live tracking Leaflet map.
5. **Two-Factor OTP Security**:
   - Pickup OTP: Staff verifies driver at restaurant counter.
   - Delivery OTP: Customer verifies driver at doorstep.

---

## 3. Quickstart Guide (Local Development)

### Prerequisites
- Python 3.12+ (or 3.14)
- Git

### Steps
```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply database migrations
python manage.py migrate

# 4. Seed complete demo data (Idempotent: 10 users, 5 restaurants, 40+ items, coupons, CMS pages)
python manage.py seed_demo

# 5. Run the ASGI server (Handles both HTTP & WebSockets)
python manage.py runserver
# Or using Daphne directly:
# daphne -b 127.0.0.1 -p 8000 food_delivery_backend.asgi:application
```

Open your browser at `http://127.0.0.1:8000/`.

---

## 4. Running with Docker Compose (Production-Ready)

To run the complete stack including PostgreSQL 16, Redis 7, Daphne ASGI, and Celery background workers:

```bash
# Start all 4 containers in background
docker-compose up -d --build

# View container logs
docker-compose logs -f web

# Stop containers
docker-compose down
```

The web server will automatically run migrations, seed demo data, and listen on port `8000`.

---

## 5. Running the Test Suite

The test suite uses `pytest-django` and `pytest-asyncio`:

```bash
# Run all tests
source venv/bin/activate
pytest
```

### What is Tested:
- **Order State Machine**: Enforces valid transitions and rejects unauthorized or premature cancellations.
- **Price Calculation & Coupons**: Verifies subtotal, 5% GST tax, Haversine delivery fees, percentage and flat coupons with maximum discount caps.
- **Role-Based Access Control (RBAC)**: Tests customer, delivery partner, kitchen staff, and admin access against all four panels.
- **Concurrency & Race Conditions**: Tests two delivery partners simultaneously attempting to accept the exact same order using `select_for_update()`; verifies one gets `200` while the second receives `409 Conflict`.
- **CMS Visual Editor & Versioning**: Tests admin password requirement, XSS sanitization (stripping `<script>` and malicious attributes via `nh3`), version increments, and rollback to historical states.
- **WebSocket Consumers**: Verifies connection lifecycle and permission verification for live tracking and kitchen KDS screens.

---

## 6. Deployment Guidelines

### A. Deploy to Render / Railway
1. Add a **PostgreSQL** database service and a **Redis** service.
2. Set Environment Variables:
   - `DEBUG=False`
   - `DJANGO_SECRET_KEY=<generate_random_key>`
   - `ALLOWED_HOSTS=<your-app-domain>`
   - `DATABASE_URL=<postgres_connection_string>`
   - `REDIS_URL=<redis_connection_string>`
3. Build Command:
   `pip install -r requirements.txt && python manage.py migrate && python manage.py seed_demo && python manage.py collectstatic --noinput`
4. Start Command:
   `daphne -b 0.0.0.0 -p $PORT food_delivery_backend.asgi:application`

### B. Deploy to VPS (Ubuntu / Debian + Nginx + Systemd)
1. Configure Nginx as reverse proxy forwarding normal traffic and upgrade headers (`Upgrade $http_upgrade`, `Connection "upgrade"`) for `/ws/` routes to Daphne on `127.0.0.1:8000`.
2. Configure Systemd service units for `daphne` and `celery`.
3. Enable HTTPS using Let's Encrypt (`certbot --nginx`).


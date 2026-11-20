import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from apps.restaurants.models import Restaurant

User = get_user_model()

@pytest.fixture
def rbac_users(db):
    admin = User.objects.create_superuser(email='rbac_admin@quickbite.com', password='pass')
    kitchen = User.objects.create_user(email='rbac_kitchen@quickbite.com', password='pass', role='kitchen_staff')
    driver = User.objects.create_user(email='rbac_driver@quickbite.com', password='pass', role='delivery_partner')
    customer = User.objects.create_user(email='rbac_cust@quickbite.com', password='pass', role='customer')

    Restaurant.objects.create(name='Test Rest', address='Test Addr', phone='1234')

    return {
        'admin': admin,
        'kitchen': kitchen,
        'driver': driver,
        'customer': customer,
    }


def test_unauthenticated_user_redirected_to_login():
    client = Client()
    res = client.get('/admin-panel/')
    assert res.status_code == 302
    assert '/accounts/login/' in res.url

    res2 = client.get('/kitchen/dashboard/')
    assert res2.status_code == 302
    assert '/accounts/login/' in res2.url


def test_customer_cannot_access_admin_or_kitchen(rbac_users):
    client = Client()
    client.force_login(rbac_users['customer'])

    # Customer accessing admin panel should be redirected away
    res = client.get('/admin-panel/')
    assert res.status_code == 302
    assert res.url == '/'

    # Customer accessing kitchen panel
    res2 = client.get('/kitchen/dashboard/')
    assert res2.status_code == 302
    assert res2.url == '/'


def test_authorized_roles_can_access_their_panels(rbac_users):
    client = Client()

    # Admin accesses admin panel
    client.force_login(rbac_users['admin'])
    res_admin = client.get('/admin-panel/')
    assert res_admin.status_code == 200

    # Kitchen staff accesses kitchen dashboard
    client.force_login(rbac_users['kitchen'])
    res_kitchen = client.get('/kitchen/dashboard/')
    assert res_kitchen.status_code == 200

    # Delivery partner accesses delivery dashboard
    client.force_login(rbac_users['driver'])
    res_driver = client.get('/delivery/dashboard/')
    assert res_driver.status_code == 200


import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.cms.models import CMSPage, CMSPageVersion
from apps.cms.sanitizer import sanitize_html

User = get_user_model()

@pytest.fixture
def cms_setup(db):
    admin = User.objects.create_superuser(email='kuxhagr@quickbite.com', password='adminsecretpassword')
    page = CMSPage.objects.create(
        title='Homepage Test',
        route='/',
        current_version=1,
        is_published=True,
        updated_by=admin
    )
    v1 = CMSPageVersion.objects.create(
        page=page,
        version_number=1,
        content_blocks={'hero_title': 'Initial Headline'},
        change_summary='Initial v1',
        created_by=admin
    )
    return {'admin': admin, 'page': page, 'v1': v1}


def test_save_version_requires_admin_password(cms_setup):
    admin = cms_setup['admin']
    page = cms_setup['page']
    client = APIClient()
    client.force_authenticate(user=admin)

    # Wrong password attempt
    res = client.post(f'/cms/api/editor/{page.id}/save/', {
        'admin_password': 'wrongpassword',
        'blocks': {'hero_title': 'New Title'}
    }, format='json')
    assert res.status_code == 401
    assert 'Invalid admin password' in res.data['error']


def test_save_version_sanitizes_xss_and_increments_version(cms_setup):
    admin = cms_setup['admin']
    page = cms_setup['page']
    client = APIClient()
    client.force_authenticate(user=admin)

    dirty_payload = {
        'admin_password': 'adminsecretpassword',
        'change_note': 'Updated banner with styling',
        'blocks': {
            'hero_title': 'Fresh Burgers <script>alert("hack")</script>',
            'banner_text': '<b>50% OFF</b> <img src=x onerror=alert(1)>'
        }
    }

    res = client.post(f'/cms/api/editor/{page.id}/save/', dirty_payload, format='json')
    assert res.status_code == 200
    assert res.data['version_number'] == 2

    page.refresh_from_db()
    assert page.current_version == 2

    v2 = CMSPageVersion.objects.get(page=page, version_number=2)
    # Ensure <script> and onerror attribute was stripped completely
    assert '<script>' not in v2.content_blocks['hero_title']
    assert 'alert(' not in v2.content_blocks['hero_title']
    assert 'onerror' not in v2.content_blocks['banner_text']


def test_rollback_version_creates_new_version_with_restored_content(cms_setup):
    admin = cms_setup['admin']
    page = cms_setup['page']
    client = APIClient()
    client.force_authenticate(user=admin)

    # Create v2
    CMSPageVersion.objects.create(
        page=page,
        version_number=2,
        content_blocks={'hero_title': 'Title Two'},
        change_summary='Second version',
        created_by=admin
    )
    page.current_version = 2
    page.save()

    # Rollback to v1
    res = client.post(f'/cms/api/editor/{page.id}/rollback/', {
        'target_version': 1
    }, format='json')

    assert res.status_code == 200
    assert res.data['version_number'] == 3

    page.refresh_from_db()
    assert page.current_version == 3
    v3 = CMSPageVersion.objects.get(page=page, version_number=3)
    assert v3.content_blocks['hero_title'] == 'Initial Headline'


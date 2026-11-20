from django.urls import path
from . import views

app_name = 'cms'

urlpatterns = [
    path('pages/', views.cms_pages_list_view, name='pages_list'),
    path('editor/<uuid:page_id>/', views.cms_visual_editor_view, name='visual_editor'),
    path('history/<uuid:page_id>/', views.cms_version_history_view, name='version_history'),

    # APIs
    path('api/editor/<uuid:page_id>/save/', views.SavePageVersionAPI.as_view(), name='api_save_version'),
    path('api/editor/<uuid:page_id>/rollback/', views.RollbackVersionAPI.as_view(), name='api_rollback_version'),
    path('api/upload-media/', views.UploadMediaAPI.as_view(), name='api_upload_media'),
]


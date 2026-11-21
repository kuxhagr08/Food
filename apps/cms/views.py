import os
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import View, ListView
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.db import transaction
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from apps.core.decorators import role_required
from .models import CMSPage, CMSPageVersion
from .sanitizer import sanitize_html, sanitize_text


def kuxhagr_required(view_func):
    """
    Strict permission check: ensures only the master superuser 'kuxhagr'
    has access to view or modify website content and CMS configurations.
    """
    def _wrapped(request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.username == 'kuxhagr'):
            messages.error(request, "Website editing and CMS are strictly restricted to master administrator (kuxhagr).")
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return _wrapped


@kuxhagr_required
def cms_pages_list_view(request):
    query = request.GET.get('q', '').strip()
    pages = CMSPage.objects.all().select_related('updated_by').order_by('route')
    if query:
        pages = pages.filter(title__icontains=query) | pages.filter(route__icontains=query)
    return render(request, 'cms/pages_list.html', {'pages': pages, 'search_query': query})


@kuxhagr_required
def cms_visual_editor_view(request, page_id):
    page = get_object_or_404(CMSPage, id=page_id)
    latest_version = page.versions.filter(version_number=page.current_version).first()
    return render(request, 'cms/visual_editor.html', {
        'page': page,
        'current_version': latest_version,
    })


@kuxhagr_required
def cms_version_history_view(request, page_id):
    page = get_object_or_404(CMSPage, id=page_id)
    versions = page.versions.all().select_related('created_by').order_by('-version_number')
    return render(request, 'cms/version_history.html', {
        'page': page,
        'versions': versions,
    })


class SavePageVersionAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, page_id):
        user = request.user
        if not (user.is_authenticated and user.username == 'kuxhagr'):
            return Response({'error': 'Website editing is strictly restricted to master administrator (kuxhagr).'}, status=status.HTTP_403_FORBIDDEN)

        page = get_object_or_404(CMSPage, id=page_id)

        # 1. Require Admin Password Confirmation
        admin_password = request.data.get('admin_password', '')
        if not user.check_password(admin_password):
            return Response({'error': 'Invalid admin password confirmation.'}, status=status.HTTP_401_UNAUTHORIZED)

        change_note = request.data.get('change_note', '').strip() or 'Updated content via Visual Editor'
        raw_blocks = request.data.get('blocks', {})

        # 2. Sanitize HTML/text to prevent XSS
        sanitized_blocks = {}
        for key, val in raw_blocks.items():
            if isinstance(val, str):
                sanitized_blocks[key] = sanitize_html(val)
            else:
                sanitized_blocks[key] = val

        with transaction.atomic():
            new_version_num = page.current_version + 1
            version_obj = CMSPageVersion.objects.create(
                page=page,
                version_number=new_version_num,
                content_blocks=sanitized_blocks,
                change_summary=change_note,
                created_by=user
            )

            page.current_version = new_version_num
            page.updated_by = user
            page.save()

            # 3. Invalidate cache for this page
            for key in sanitized_blocks.keys():
                cache.delete(f"cms_block_{page.route}_{key}")
                cache.delete(f"cms_img_{page.route}_{key}")

        return Response({
            'success': True,
            'version_number': new_version_num,
            'message': f"Version {new_version_num} saved successfully!"
        })


class UploadMediaAPI(APIView):
    """Allows uploading replacement images/videos in visual editor with extension & size validation."""
    permission_classes = [permissions.IsAuthenticated]

    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.svg', '.gif', '.mp4'}
    MAX_SIZE = 5 * 1024 * 1024  # 5 MB

    def post(self, request):
        if not (request.user.is_authenticated and request.user.username == 'kuxhagr'):
            return Response({'error': 'Website editing is strictly restricted to master administrator (kuxhagr).'}, status=status.HTTP_403_FORBIDDEN)

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            return Response({'error': f'Unsupported file extension: {ext}'}, status=status.HTTP_400_BAD_REQUEST)

        if uploaded_file.size > self.MAX_SIZE:
            return Response({'error': 'File size exceeds 5MB limit.'}, status=status.HTTP_400_BAD_REQUEST)

        # Save with safe random name
        safe_filename = f"cms/{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(safe_filename, uploaded_file)
        file_url = default_storage.url(saved_path)

        return Response({'success': True, 'url': file_url})


class RollbackVersionAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, page_id):
        user = request.user
        if not (user.is_authenticated and user.username == 'kuxhagr'):
            return Response({'error': 'Website editing is strictly restricted to master administrator (kuxhagr).'}, status=status.HTTP_403_FORBIDDEN)

        page = get_object_or_404(CMSPage, id=page_id)
        target_version_num = int(request.data.get('target_version', 1))

        target_version = get_object_or_404(CMSPageVersion, page=page, version_number=target_version_num)

        with transaction.atomic():
            new_version_num = page.current_version + 1
            CMSPageVersion.objects.create(
                page=page,
                version_number=new_version_num,
                content_blocks=target_version.content_blocks,
                change_summary=f"Rollback to Version {target_version_num}",
                created_by=user
            )
            page.current_version = new_version_num
            page.updated_by = user
            page.save()

            # Invalidate cache
            for key in target_version.content_blocks.keys():
                cache.delete(f"cms_block_{page.route}_{key}")
                cache.delete(f"cms_img_{page.route}_{key}")

        return Response({
            'success': True,
            'version_number': new_version_num,
            'message': f"Rolled back to Version {target_version_num} as new Version {new_version_num}!"
        })


import uuid
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel

class CMSPage(BaseModel):
    title = models.CharField(max_length=150)
    route = models.CharField(max_length=200, unique=True, db_index=True) # e.g. '/', '/about/', '/contact/'
    current_version = models.PositiveIntegerField(default=1)
    is_published = models.BooleanField(default=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cms_pages_edited'
    )

    class Meta:
        verbose_name = 'CMS Page'
        verbose_name_plural = 'CMS Pages'
        ordering = ['route']

    def __str__(self):
        return f"{self.title} ({self.route}) - v{self.current_version}"

    def get_active_blocks(self):
        latest_version = self.versions.filter(version_number=self.current_version).first()
        if latest_version:
            return latest_version.content_blocks
        return {}


class CMSPageVersion(BaseModel):
    page = models.ForeignKey(CMSPage, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    content_blocks = models.JSONField(default=dict)
    change_summary = models.CharField(max_length=255, default='Updated page content')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cms_versions_created'
    )

    class Meta:
        verbose_name = 'CMS Page Version'
        verbose_name_plural = 'CMS Page Versions'
        ordering = ['-version_number']
        unique_together = ('page', 'version_number')

    def __str__(self):
        return f"{self.page.title} - Version {self.version_number} by {self.created_by}"


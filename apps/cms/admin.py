from django.contrib import admin
from .models import CMSPage, CMSPageVersion

class CMSPageVersionInline(admin.TabularInline):
    model = CMSPageVersion
    extra = 0
    readonly_fields = ('version_number', 'change_summary', 'created_by', 'created_at')

@admin.register(CMSPage)
class CMSPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'route', 'current_version', 'is_published', 'updated_at', 'updated_by')
    list_filter = ('is_published', 'updated_at')
    search_fields = ('title', 'route')
    inlines = [CMSPageVersionInline]

@admin.register(CMSPageVersion)
class CMSPageVersionAdmin(admin.ModelAdmin):
    list_display = ('page', 'version_number', 'change_summary', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('page__title', 'change_summary')


from django import template
from django.utils.safestring import mark_safe
from django.core.cache import cache
from apps.cms.models import CMSPage
from apps.cms.sanitizer import sanitize_html

register = template.Library()

@register.simple_tag(takes_context=True)
def cms_block(context, route, key, default_content=""):
    """
    Renders an editable CMS block.
    If 'cms_preview' or 'cms_edit' is active in context, wraps it with editable markup.
    """
    request = context.get('request')
    is_edit_mode = False
    if request and request.GET.get('cms_edit') == '1' and (request.user.is_authenticated and (request.user.role == 'admin' or request.user.is_superuser)):
        is_edit_mode = True

    cache_key = f"cms_block_{route}_{key}"
    cached_val = cache.get(cache_key)

    if cached_val is None:
        try:
            page = CMSPage.objects.filter(route=route).first()
            if page:
                blocks = page.get_active_blocks()
                cached_val = blocks.get(key, default_content)
            else:
                cached_val = default_content
        except Exception:
            cached_val = default_content
        cache.set(cache_key, cached_val, timeout=300)

    content = cached_val or default_content

    if is_edit_mode:
        return mark_safe(f'<span class="cms-editable-inline" data-cms-key="{key}" contenteditable="true" title="Click to edit text">{content}</span>')
    return mark_safe(content)


@register.simple_tag(takes_context=True)
def cms_image(context, route, key, default_src="", alt_text=""):
    request = context.get('request')
    is_edit_mode = False
    if request and request.GET.get('cms_edit') == '1' and (request.user.is_authenticated and (request.user.role == 'admin' or request.user.is_superuser)):
        is_edit_mode = True

    cache_key = f"cms_img_{route}_{key}"
    cached_src = cache.get(cache_key)

    if cached_src is None:
        try:
            page = CMSPage.objects.filter(route=route).first()
            if page:
                blocks = page.get_active_blocks()
                cached_src = blocks.get(key, default_src)
            else:
                cached_src = default_src
        except Exception:
            cached_src = default_src
        cache.set(cache_key, cached_src, timeout=300)

    src = cached_src or default_src

    if is_edit_mode:
        return mark_safe(f'<div class="cms-image-wrapper" data-cms-image-key="{key}"><img src="{src}" alt="{alt_text}" data-cms-img="{key}"><button type="button" class="cms-img-change-btn" onclick="window.parent.triggerImageUpload(\'{key}\')">📷 Replace</button></div>')
    return mark_safe(f'<img src="{src}" alt="{alt_text}">')


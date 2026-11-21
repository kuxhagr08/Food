from django import template
from django.utils.html import format_html, escape
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
    if request and request.GET.get('cms_edit') == '1' and (request.user.is_authenticated and request.user.username == 'kuxhagr'):
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

    raw_content = cached_val or default_content
    # Sanitize content with nh3 whitelist to prevent XSS
    sanitized = sanitize_html(str(raw_content))
    content_safe = mark_safe(sanitized)  # nosec B308, B703 - sanitized with nh3 whitelist

    if is_edit_mode:
        return format_html(
            '<span class="cms-editable-inline" data-cms-key="{}" contenteditable="true" title="Click to edit text">{}</span>',
            key,
            content_safe
        )
    return content_safe


@register.simple_tag(takes_context=True)
def cms_image(context, route, key, default_src="", alt_text=""):
    request = context.get('request')
    is_edit_mode = False
    if request and request.GET.get('cms_edit') == '1' and (request.user.is_authenticated and request.user.username == 'kuxhagr'):
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
        return format_html(
            '<div class="cms-image-wrapper" data-cms-image-key="{0}"><img src="{1}" alt="{2}" data-cms-img="{0}"><button type="button" class="cms-img-change-btn" onclick="window.parent.triggerImageUpload(\'{0}\')">📷 Replace</button></div>',
            key,
            src,
            alt_text
        )
    return format_html('<img src="{}" alt="{}">', src, alt_text)


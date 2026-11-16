from .models import WebsitePage, WebSetting


def public_pages(request):
    site_settings = WebSetting.objects.first()
    if request.path.startswith('/dashboard/') or request.path.startswith('/admin/'):
        return {'public_pages': [], 'site_settings': site_settings}
    return {
        'public_pages': WebsitePage.objects.filter(
            status=WebsitePage.Status.PUBLISHED,
        ).order_by('judul'),
        'site_settings': site_settings,
    }

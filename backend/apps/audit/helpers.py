from django.utils import timezone


def active_grant_org_ids(request):
    """
    Return the set of organisation PKs that have an active DataAccessGrant.
    Result is cached on the request object for the duration of the request.
    """
    if not hasattr(request, '_active_grant_org_ids'):
        from apps.audit.models import DataAccessGrant
        request._active_grant_org_ids = set(
            DataAccessGrant.objects
            .filter(is_revoked=False, expires_at__gt=timezone.now())
            .values_list('organisation_id', flat=True)
        )
    return request._active_grant_org_ids


class DataAccessMixin:
    """
    Mixin for ModelAdmin classes whose objects belong to an Organisation.
    Assumes the model has an `organisation` / `organisation_id` FK.

    - List views: sensitive columns show [REDACTED] when no active grant exists.
    - Detail views: blocked entirely with an access-denied page.
    """

    def changelist_view(self, request, extra_context=None):
        self._request = request
        return super().changelist_view(request, extra_context)

    def _has_grant(self, obj):
        org_id = getattr(obj, 'organisation_id', None)
        if org_id is None:
            return True
        return org_id in active_grant_org_ids(self._request)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)
        if obj:
            org_id = getattr(obj, 'organisation_id', None)
            if org_id and org_id not in active_grant_org_ids(request):
                from django.shortcuts import render
                return render(request, 'admin/audit/access_denied.html', {
                    **self.admin_site.each_context(request),
                    'title': 'Data Access Restricted',
                    'organisation': obj.organisation,
                    'opts': self.model._meta,
                })
        return super().change_view(request, object_id, form_url, extra_context)

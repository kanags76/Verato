from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/v1/', include([
        # Auth
        path('auth/token/',           TokenObtainPairView.as_view(),  name='token_obtain_pair'),
        path('auth/token/refresh/',   TokenRefreshView.as_view(),     name='token_refresh'),
        path('auth/token/blacklist/', TokenBlacklistView.as_view(),   name='token_blacklist'),
        # App routers
        path('', include('apps.accounts.urls')),
        path('', include('apps.meetings.urls')),
        path('', include('apps.commitments.urls')),
        path('', include('apps.analytics.urls')),
    ])),

    path('api/schema/',       SpectacularAPIView.as_view(),                      name='schema'),
    path('api/schema/ui/',    SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'),   name='redoc'),

    path('api/health/', lambda request: JsonResponse({'status': 'ok', 'version': '0.1.0'})),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]

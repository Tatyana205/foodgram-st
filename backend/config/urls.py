from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.views.generic import TemplateView
from recipes.views import RecipeViewSet
from users.views import UserAvatarView

schema_view = get_schema_view(
    openapi.Info(
        title="Foodgram API",
        default_version='v1',
        description="API для проекта Foodgram",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@foodgram.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
    path('admin/', admin.site.urls),
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.jwt')),
    path('api/users/me/avatar/', UserAvatarView.as_view(), name='user-avatar'),
    path('api/ingredients/', include('ingredients.urls')),
    path('api/recipes/<int:pk>/get-link/', 
         RecipeViewSet.as_view({'get': 'get_link'}), 
         name='recipe-get-link'),
    path('api/', include('users.urls')),
    path('api/', include('recipes.urls')),
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

urlpatterns += [
    path('', TemplateView.as_view(template_name='index.html')),
    # path('<path:path>', TemplateView.as_view(template_name='index.html')),
    re_path(r'^.*$', TemplateView.as_view(template_name='index.html')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

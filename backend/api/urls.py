from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from api.views import IngredientViewSet, RecipeViewSet, UserViewSet

router = DefaultRouter()
router.register("recipes", RecipeViewSet, basename="recipes")
router.register("users", UserViewSet, basename="users")

schema_view = get_schema_view(
    openapi.Info(
        title="Foodgram API",
        default_version="v1",
        description="API для проекта Foodgram",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@foodgram.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path(
        "users/<int:pk>/subscribe/",
        UserViewSet.as_view({"post": "subscribe", "delete": "subscribe"}),
        name="subscribe",
    ),
    path("", include(router.urls)),
    path(
        "ingredients/", IngredientViewSet.as_view({"get": "list"}), name="ingredients"
    ),
    path("auth/", include("djoser.urls.authtoken")),
    path(
        "recipes/<int:pk>/get-link/",
        RecipeViewSet.as_view({"get": "get_link"}),
        name="recipe-get-link",
    ),
    path(
        "docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

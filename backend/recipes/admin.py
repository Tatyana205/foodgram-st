from django.contrib import admin
from django.db.models import Count

from .models import Favorite, Ingredient, Recipe, RecipeIngredient, ShoppingCart


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "measurement_unit")
    search_fields = ("name",)
    list_filter = ("measurement_unit",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "author")
    list_display_links = ("name",)
    search_fields = ("name", "author__email")
    list_filter = ("created",)
    inlines = (RecipeIngredientInline,)
    readonly_fields = ("favorites_count_display",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return (
            qs.select_related("author")
            .prefetch_related("recipe_ingredients__ingredient")
            .annotate(favorites_count=Count("in_favorites"))
        )

    def favorites_count_display(self, obj):
        return obj.favorites_count or 0

    favorites_count_display.short_description = "В избранном"


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe", "created")
    list_display_links = ("user", "recipe")
    search_fields = ("user__email", "recipe__name")
    list_filter = ("created",)


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe", "created")
    list_display_links = ("user", "recipe")
    search_fields = ("user__email", "recipe__name")
    list_filter = ("created",)

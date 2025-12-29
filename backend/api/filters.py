import django_filters

from recipes.models import Favorite, Recipe, ShoppingCart


class RecipeFilter(django_filters.FilterSet):
    is_favorited = django_filters.CharFilter(method="filter_is_favorited")
    is_in_shopping_cart = django_filters.CharFilter(method="filter_is_in_shopping_cart")
    author = django_filters.NumberFilter(field_name="author__id")

    class Meta:
        model = Recipe
        fields = ["author", "is_favorited", "is_in_shopping_cart"]

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            favorite_ids = Favorite.objects.filter(user=user).values_list(
                "recipe_id", flat=True
            )
            return queryset.filter(id__in=favorite_ids)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            cart_ids = ShoppingCart.objects.filter(user=user).values_list(
                "recipe_id", flat=True
            )
            return queryset.filter(id__in=cart_ids)
        return queryset

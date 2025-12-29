from io import BytesIO

from django.db.models import Exists, OuterRef, Sum
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from api.filters import RecipeFilter
from api.serializers.recipes import (
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeSerializer,
)
from recipes.models import Favorite, Ingredient, Recipe, RecipeIngredient, ShoppingCart


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    pagination_class = None
    http_method_names = ["get"]

    def get_queryset(self):
        return Ingredient.objects.all()

    def list(self, request, *args, **kwargs):
        name = request.query_params.get("name")

        if name:
            queryset = self.get_queryset().filter(name__istartswith=name)
        else:
            queryset = self.get_queryset().none()

        queryset = queryset[:10]

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PageNumberPagination

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return RecipeCreateSerializer
        return RecipeSerializer

    def get_queryset(self):
        queryset = (
            Recipe.objects.all()
            .select_related("author")
            .prefetch_related("recipe_ingredients__ingredient")
        )

        user = self.request.user
        if user.is_authenticated:
            queryset = queryset.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(user=user, recipe=OuterRef("pk"))
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(user=user, recipe=OuterRef("pk"))
                ),
            )
        else:
            pass

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def _handle_subscription(self, request, recipe, model, action_name):
        user = request.user

        if request.method == "POST":
            obj, created = model.objects.get_or_create(user=user, recipe=recipe)
            if not created:
                return Response(
                    {"error": f"Рецепт уже в {action_name}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"success": f"Рецепт добавлен в {action_name}"},
                status=status.HTTP_201_CREATED,
            )

        if request.method == "DELETE":
            deleted = model.objects.filter(user=user, recipe=recipe).delete()[0]
            if not deleted:
                return Response(
                    {"error": f"Рецепт не был в {action_name}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        return self._handle_subscription(request, recipe, Favorite, "избранное")

    @action(
        detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        return self._handle_subscription(
            request, recipe, ShoppingCart, "список покупок"
        )

    def _generate_shopping_list_buffer(self, ingredients):
        buffer = BytesIO()
        lines = ["Список покупок:\n\n"]

        for item in ingredients:
            name = item["ingredient__name"]
            unit = item["ingredient__measurement_unit"]
            amount = item["total_amount"]
            lines.append(f"- {name} ({unit}) — {amount}\n")

        lines.append("\nКонец списка")

        content = "".join(lines).encode("utf-8")
        buffer.write(content)
        buffer.seek(0)
        return buffer

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        ingredients = (
            RecipeIngredient.objects.filter(recipe__in_shopping_cart__user=request.user)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )

        if not ingredients:
            return Response(
                {"error": "Список покупок пуст"}, status=status.HTTP_400_BAD_REQUEST
            )

        buffer = self._generate_shopping_list_buffer(ingredients)

        response = Response(
            buffer.getvalue().decode("utf-8"), content_type="text/plain; charset=utf-8"
        )
        response["Content-Disposition"] = 'attachment; filename="shopping_list.txt"'
        return response

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def favorites(self, request):
        favorite_ids = Favorite.objects.filter(user=request.user).values_list(
            "recipe_id", flat=True
        )

        queryset = self.get_queryset().filter(id__in=favorite_ids)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def get_link(self, request, pk=None):
        recipe = self.get_object()

        recipe_url = request.build_absolute_uri(f"/recipes/{recipe.id}/")

        return Response(
            {
                "short-link": recipe_url,
                "recipe_id": recipe.id,
                "recipe_name": recipe.name,
            }
        )

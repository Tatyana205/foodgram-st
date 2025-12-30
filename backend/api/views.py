from io import BytesIO

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, Sum
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.filters import SearchFilter

from api.serializers import (
    SubscriptionCreateSerializer,
    SubscriptionUserSerializer,
    UserAvatarSerializer,
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeSerializer,
    FavoriteSerializer,
    ShoppingCartSerializer
)
from api.filters import RecipeFilter, IngredientSearchFilter
from recipes.models import Favorite, Ingredient, Recipe, RecipeIngredient, ShoppingCart
from users.models import Subscription

User = get_user_model()


class SubscriptionPagination(PageNumberPagination):
    page_size = 6
    page_size_query_param = "page_size"
    max_page_size = 100


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    pagination_class = SubscriptionPagination

    permission_classes_by_action = {
        "create": [AllowAny],
        "list": [AllowAny],
        "retrieve": [AllowAny],
        "me": [IsAuthenticated],
        "subscribe": [IsAuthenticated],
        "subscriptions": [IsAuthenticated],
        "set_password": [IsAuthenticated],
        "update": [IsAuthenticated],
        "partial_update": [IsAuthenticated],
        "destroy": [IsAuthenticated],
    }

    def get_serializer_class(self):
        if self.action == "create":
            from api.serializers import UserCreateSerializer

            return UserCreateSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action in self.permission_classes_by_action:
            return [perm() for perm in self.permission_classes_by_action[self.action]]
        return [IsAuthenticated()]

    @action(
        detail=False,
        methods=["put", "delete"],
        permission_classes=[IsAuthenticated],
        url_path="me/avatar",
        url_name="me-avatar",
    )
    def avatar(self, request):
        user = request.user

        if request.method == "DELETE":
            if user.avatar:
                user.avatar.delete()
            serializer = self.get_serializer(user)
            return Response(serializer.data)

        if request.method == "PUT":
            serializer = UserAvatarSerializer(
                user, data=request.data, partial=True, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(
        detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, pk=None, **kwargs):
        author = get_object_or_404(User, pk=pk)

        if request.method == "POST":
            serializer = SubscriptionCreateSerializer(
                data={"author": author.id}, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            author_serializer = SubscriptionUserSerializer(
                author, context={"request": request}
            )

            return Response(author_serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            deleted_count, _ = Subscription.objects.filter(
                user=request.user, author=author
            ).delete()
            if not deleted_count == 0:
                return Response(
                    {"error": "Вы не подписаны на этого пользователя"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        queryset = User.objects.filter(following__user=request.user).annotate(
            recipes_count=Count("recipes")
        )

        page = self.paginate_queryset(queryset)
        serializer = SubscriptionUserSerializer(
            page if page is not None else queryset,
            many=True,
            context={"request": request},
        )
        return (
            self.get_paginated_response(serializer.data)
            if page is not None
            else Response(serializer.data)
        )


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    pagination_class = None
    http_method_names = ["get"]
    filter_backends = [IngredientSearchFilter]
    search_fields = ["^name"]

    def get_queryset(self):
        return Ingredient.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        if "name" not in request.query_params:
            return Response([])

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
            Recipe.objects
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

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def _handle_subscription(self, request, pk, model, serializer_class, action_name):
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == "POST":
            data = {
                "user": request.user.id,
                "recipe": recipe.id,
            }
            serializer = serializer_class(
                data=data,
                context=self.get_serializer_context()
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "DELETE":
            deleted_count, _ = model.objects.filter(user=request.user, recipe=recipe).delete()
            if deleted_count == 0:
                return Response(
                    {"error": f"Рецепт не был в {action_name}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        return self._handle_subscription(
            request, pk, Favorite, FavoriteSerializer, "избранное"
        )

    @action(
        detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        return self._handle_subscription(
            request, pk, ShoppingCart, ShoppingCartSerializer, "список покупок"
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
            RecipeIngredient.objects.filter(recipe__in_shoppingcarts__user=request.user)
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

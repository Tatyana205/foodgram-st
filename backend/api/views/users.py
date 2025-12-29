from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import parsers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.users import (
    SubscriptionCreateSerializer,
    SubscriptionUserSerializer,
    UserAvatarSerializer,
)
from users.models import Subscription

User = get_user_model()


class SubscriptionPagination(PageNumberPagination):
    page_size = 10
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
            from api.serializers.users import UserCreateSerializer

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
                user.avatar.delete(save=False)
                user.avatar = None
                user.save()
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
            deleted = Subscription.objects.filter(
                user=request.user, author=author
            ).delete()[0]
            if not deleted:
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

import base64
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from djoser.serializers import UserSerializer as DjoserUserSerializer
from django.core.files.base import ContentFile
from rest_framework.validators import UniqueTogetherValidator
from rest_framework import serializers

from recipes.models import Ingredient, Recipe, RecipeIngredient, Favorite, ShoppingCart
from users.models import Subscription

User = get_user_model()


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Subscription
        fields = ("user", "author")

    def validate(self, attrs):
        author = attrs["author"]
        user = self.context["request"].user

        if author == user:
            raise serializers.ValidationError("Нельзя подписаться на самого себя.")

        if Subscription.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError("Вы уже подписаны на этого пользователя.")

        attrs["user"] = user
        return attrs

    def create(self, validated_data):
        return Subscription.objects.create(**validated_data)


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        validators=[validate_password],
    )

    class Meta:
        model = User
        fields = ["email", "username", "first_name", "last_name", "password"]
        extra_kwargs = {
            "email": {"required": True},
            "username": {"required": True},
            "first_name": {"required": False},
            "last_name": {"required": False},
        }

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class CustomUserSerializer(DjoserUserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta(DjoserUserSerializer.Meta):
        model = User
        fields = DjoserUserSerializer.Meta.fields + ("is_subscribed", "avatar")
        read_only_fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "avatar",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.following.filter(user=request.user).exists()
        return False

    def get_avatar(self, obj):
        request = self.context.get("request")
        if obj.avatar and hasattr(obj.avatar, "url"):
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class AuthorSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "avatar",
            "is_subscribed",
        ]
        read_only_fields = fields

    def get_avatar(self, obj):
        request = self.context.get("request")
        if obj.avatar and hasattr(obj.avatar, "url"):
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.following.filter(user=request.user).exists()
        return False


class SimpleRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class SubscriptionUserSerializer(CustomUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True, default=0)

    class Meta(CustomUserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + ("recipes", "recipes_count")

    def get_recipes(self, obj):
        request = self.context.get("request")
        recipes_limit = request.query_params.get("recipes_limit")
        recipes = obj.recipes.all()

        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[: int(recipes_limit)]

        return SimpleRecipeSerializer(
            recipes, many=True, context={"request": request}
        ).data


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            format, imgstr = data.split(";base64,")
            ext = format.split("/")[-1]

            data = ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")

        return super().to_internal_value(data)


class UserAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ["avatar"]

    def update(self, instance, validated_data):
        if "avatar" in validated_data:
            if instance.avatar:
                instance.avatar.delete(save=False)
            instance.avatar = validated_data["avatar"]
            instance.save()
        return instance


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source="ingredient"
    )
    name = serializers.CharField(source="ingredient.name", read_only=True)
    measurement_unit = serializers.CharField(
        source="ingredient.measurement_unit", read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source="recipe_ingredients", many=True, read_only=True
    )
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)
    image = serializers.ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "author",
            "ingredients",
            "name",
            "image",
            "text",
            "cooking_time",
            "is_favorited",
            "is_in_shopping_cart",
        )
        read_only_fields = ("id", "author", "is_favorited", "is_in_shopping_cart")

    def get_is_favorited(self, obj):
        user = self.context.get("request").user
        if user.is_authenticated:
            return obj.favorites.filter(user=user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get("request").user
        if user.is_authenticated:
            return obj.shoppingcarts.filter(user=user).exists()
        return False


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(source="recipe_ingredients", many=True)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = ("ingredients", "name", "image", "text", "cooking_time")

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Добавьте хотя бы один ингредиент")

        ingredient_ids = [item["ingredient"].id for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError("Ингредиенты не должны повторяться")

        for item in value:
            if item["amount"] <= 0:
                raise serializers.ValidationError(
                    f"Количество для ингредиента должно быть больше 0"
                )

        return value

    def validate_cooking_time(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Время приготовления должно быть больше 0 минут"
            )
        if value > 1440:  # 24 часа
            raise serializers.ValidationError(
                "Время приготовления не может быть больше 24 часов"
            )
        return value

    def validate_image(self, value):
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("Файл слишком большой (макс. 5MB)")
        return value

    def _save_ingredients(self, recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    recipe=recipe, ingredient=item["ingredient"], amount=item["amount"]
                )
                for item in ingredients_data
            ]
        )

    def create(self, validated_data):
        if "recipe_ingredients" not in validated_data:
            raise serializers.ValidationError("Не указаны ингредиенты")

        ingredients_data = validated_data.pop("recipe_ingredients")
        recipe = Recipe.objects.create(**validated_data)
        self._save_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        if "recipe_ingredients" in validated_data:
            instance.recipe_ingredients.all().delete()
            ingredients_data = validated_data.pop("recipe_ingredients")
            self._save_ingredients(instance, ingredients_data)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeSerializer(instance, context=self.context).data


class ShortRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")

class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ("user", "recipe")
        validators = [
            UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=("user", "recipe"),
                message="Рецепт уже в избранном",
            )
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].required = False
        self.fields["recipe"].required = False

    def to_representation(self, instance):
        return RecipeSerializer(
            instance.recipe,
            context=self.context
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ("user", "recipe")
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=("user", "recipe"),
                message="Рецепт уже в списке покупок",
            )
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].required = False
        self.fields["recipe"].required = False

    def to_representation(self, instance):
        return RecipeSerializer(
            instance.recipe,
            context=self.context
        ).data

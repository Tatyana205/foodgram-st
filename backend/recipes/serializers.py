from rest_framework import serializers
from .models import Recipe, RecipeIngredient, Favorite, ShoppingCart, User
from ingredients.models import Ingredient, Tag
from ingredients.serializers import IngredientSerializer, TagSerializer
import base64
import uuid
from django.core.files.base import ContentFile


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            
            data = ContentFile(
                base64.b64decode(imgstr),
                name=f'{uuid.uuid4()}.{ext}'
            )
        
        return super().to_internal_value(data)


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name',
            'image', 'text', 'cooking_time',
            'is_favorited', 'is_in_shopping_cart'
        )
        read_only_fields = ('id', 'author')

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return obj.favorites.filter(user=user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return obj.shopping_cart.filter(user=user).exists()
        return False


class RecipeCreateSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=False
    )
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'tags', 'name', 'image',
            'text', 'cooking_time'
        )

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                "Добавьте хотя бы один ингредиент"
            )
        
        ingredient_ids = [item['ingredient'].id for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                "Ингредиенты не должны повторяться"
            )
        
        for item in value:
            if item['amount'] <= 0:
                raise serializers.ValidationError(
                    f"Количество для ингредиента должно быть больше 0"
                )
        
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError(
                "Добавьте хотя бы один тег"
            )
        
        if len(value) != len(set([tag.id for tag in value])):
            raise serializers.ValidationError(
                "Теги не должны повторяться"
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

    def create(self, validated_data):
        if 'recipe_ingredients' not in validated_data:
            raise serializers.ValidationError("Не указаны ингредиенты")
        
        ingredients_data = validated_data.pop('recipe_ingredients')
        tags_data = validated_data.pop('tags', [])
        
        recipe = Recipe.objects.create(**validated_data)
        
        recipe.tags.set(tags_data)
        
        for item in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item['amount']
            )
        
        return recipe

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.image = validated_data.get('image', instance.image)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get('cooking_time', instance.cooking_time)
        instance.save()
        
        if 'tags' in validated_data:
            tags_data = validated_data.pop('tags')
            instance.tags.set(tags_data)
        
        if 'recipe_ingredients' in validated_data:
            instance.recipe_ingredients.all().delete()
            
            ingredients_data = validated_data.pop('recipe_ingredients')
            for ingredient_data in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=ingredient_data['ingredient'],
                    amount=ingredient_data['amount']
                )
        
        return instance


class ShortRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

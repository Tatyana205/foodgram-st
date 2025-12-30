from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from users.models import User

from .constants import (
    MAX_COOKING_TIME,
    MAX_INGREDIENT_AMOUNT,
    MIN_COOKING_TIME,
    MIN_INGREDIENT_AMOUNT,
)


class Ingredient(models.Model):
    name = models.CharField("Название", max_length=200)
    measurement_unit = models.CharField("Единица измерения", max_length=200)

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "measurement_unit"], name="unique_ingredient"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор"
    )
    name = models.CharField(max_length=200, verbose_name="Название")
    image = models.ImageField(upload_to="recipes/", verbose_name="Картинка")
    text = models.TextField(verbose_name="Описание")
    ingredients = models.ManyToManyField(
        Ingredient, through="RecipeIngredient", verbose_name="Ингредиенты"
    )
    cooking_time = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_COOKING_TIME),
            MaxValueValidator(MAX_COOKING_TIME),
        ],
        verbose_name="Время приготовления (в минутах)",
    )
    created = models.DateTimeField(auto_now_add=True, verbose_name="Дата публикации")

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        ordering = ["-created"]

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients"
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, verbose_name="Ингредиент"
    )
    amount = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_INGREDIENT_AMOUNT),
            MaxValueValidator(MAX_INGREDIENT_AMOUNT),
        ],
        verbose_name="Количество",
    )

    class Meta:
        verbose_name = "Ингредиент рецепта"
        verbose_name_plural = "Ингредиенты рецепта"
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"], name="unique_recipe_ingredient"
            )
        ]

    def __str__(self):
        return (
            f"{self.ingredient.name} - {self.amount} {self.ingredient.measurement_unit}"
        )


class UserRecipeRelation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        verbose_name="Пользователь"
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="in_%(class)ss",
        verbose_name="Рецепт"
    )
    created = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="%(app_label)s_%(class)s_unique_user_recipe",
            )
        ]

    def __str__(self):
        return f"{self.user} — {self.recipe}"


class Favorite(UserRecipeRelation):
    class Meta(UserRecipeRelation.Meta):
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"


class ShoppingCart(UserRecipeRelation):
    class Meta(UserRecipeRelation.Meta):
        verbose_name = "Список покупок"
        verbose_name_plural = "Списки покупок"

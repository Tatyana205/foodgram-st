from django.contrib import admin
from .models import Recipe, RecipeIngredient, Favorite, ShoppingCart

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author', 'cooking_time', 'created')
    search_fields = ('name', 'author__email')
    list_filter = ('tags', 'created')
    inlines = (RecipeIngredientInline,)

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe', 'created')

@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe', 'created')

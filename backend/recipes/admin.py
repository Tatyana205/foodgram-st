from django.contrib import admin
from .models import Recipe, RecipeIngredient, Favorite, ShoppingCart

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author')
    search_fields = ('name', 'author__email')
    list_filter = ('created',)
    inlines = (RecipeIngredientInline,)

    fieldsets = (
        (None, {
            'fields': ('name', 'author', 'image', 'text', 'cooking_time')
        }),
        ('Статистика', {
            'fields': ('favorites_count_display',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('favorites_count_display',)

    def favorites_count_display(self, obj):
        count = obj.favorites.count()
        return f"Этот рецепт добавлен в избранное {count} раз(а)"
    favorites_count_display.short_description = 'Добавлений в избранное'

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe', 'created')

@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe', 'created')

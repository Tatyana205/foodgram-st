from django.test import TestCase
from django.contrib.auth import get_user_model
from recipes.models import Recipe

User = get_user_model()

class RecipeBasicTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='recipeuser@example.com',
            username='recipeuser',
            password='pass123'
        )
    
    def test_recipe_creation(self):
        recipe = Recipe.objects.create(
            author=self.user,
            name='Базовый рецепт',
            text='Описание',
            cooking_time=30
        )
        self.assertEqual(recipe.author, self.user)
    
    def test_recipe_image_field(self):
        recipe = Recipe.objects.create(
            author=self.user,
            name='Рецепт с картинкой',
            text='Описание',
            cooking_time=25
        )
        self.assertTrue(hasattr(recipe, 'image'))

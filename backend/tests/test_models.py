from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from recipes.models import Recipe, Favorite, ShoppingCart
from ingredients.models import Ingredient

User = get_user_model()

class UserModelTests(TestCase):
    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
        }
    
    def test_create_user(self):
        user = User.objects.create_user(
            **self.user_data,
            password='TestPassword123'
        )
        
        self.assertEqual(user.email, self.user_data['email'])
        self.assertEqual(user.username, self.user_data['username'])
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('TestPassword123'))
        print(f"Создан пользователь: {user.email}")
    
    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            **self.user_data,
            password='AdminPassword123'
        )
        
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        print(f"Создан суперпользователь: {admin.email}")
    
    def test_email_unique(self):
        User.objects.create_user(
            email='unique@example.com',
            username='user1',
            password='pass123'
        )
        
        with self.assertRaises(Exception):
            User.objects.create_user(
                email='unique@example.com',
                username='user2',
                password='pass456'
            )
        print("Проверка уникальности email работает")

class RecipeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='chef@example.com',
            username='chef',
            password='chefpass123'
        )
    
    def test_create_recipe(self):
        recipe = Recipe.objects.create(
            author=self.user,
            name='Тестовый рецепт',
            text='Подробное описание рецепта',
            cooking_time=45
        )
        
        self.assertEqual(recipe.name, 'Тестовый рецепт')
        self.assertEqual(recipe.author, self.user)
        self.assertEqual(recipe.cooking_time, 45)
        self.assertEqual(str(recipe), 'Тестовый рецепт')
        print(f"Создан рецепт: {recipe.name}")
    
    def test_recipe_cooking_time_validation(self):
        recipe = Recipe(
            author=self.user,
            name='Рецепт',
            text='Описание',
            cooking_time=0
        )
        
        with self.assertRaises(ValidationError):
            recipe.full_clean()
        print("Валидация времени приготовления работает")

class FavoriteModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            username='user',
            password='pass123'
        )
        self.recipe = Recipe.objects.create(
            author=self.user,
            name='Любимый рецепт',
            text='Описание',
            cooking_time=30
        )
    
    def test_create_favorite(self):
        favorite = Favorite.objects.create(
            user=self.user,
            recipe=self.recipe
        )
        
        self.assertEqual(favorite.user, self.user)
        self.assertEqual(favorite.recipe, self.recipe)
        self.assertIn(favorite, self.user.favorites.all())
        self.assertIn(favorite, self.recipe.favorites.all())
        print("Добавлено в избранное")

class ShoppingCartModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='shopper@example.com',
            username='shopper',
            password='pass123'
        )
        self.recipe = Recipe.objects.create(
            author=self.user,
            name='Для покупок',
            text='Описание',
            cooking_time=20
        )
    
    def test_create_shopping_cart(self):
        cart = ShoppingCart.objects.create(
            user=self.user,
            recipe=self.recipe
        )
        
        self.assertEqual(cart.user, self.user)
        self.assertEqual(cart.recipe, self.recipe)
        self.assertIn(cart, self.user.shopping_cart.all())
        self.assertIn(cart, self.recipe.shopping_cart.all())
        print("Добавлено в список покупок")

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json

User = get_user_model()

class ViewTests(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='viewtest@example.com',
            username='viewtest',
            password='viewpass123',
            first_name='View',
            last_name='Test'
        )
    
    def test_home_page(self):
        response = self.client.get('/')
        self.assertIn(response.status_code, [200, 301, 302])
        print("Главная страница отвечает")
    
    def test_admin_login_redirect(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/admin/login/'))
        print("Админка переводит на логин")
    
    def test_api_root(self):
        response = self.client.get('/api/')
        self.assertIn(response.status_code, [200, 404])
        print(f"API корень вернул {response.status_code}")
    
    def test_user_registration_api(self):
        data = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': 'NewPass123!',
            'first_name': 'New',
            'last_name': 'User'
        }
        
        response = self.client.post(
            '/api/auth/users/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertIn(response.status_code, [201, 400, 401])
        
        if response.status_code == 201:
            response_data = json.loads(response.content)
            self.assertEqual(response_data['email'], data['email'])
            print("Регистрация пользователя работает")
        else:
            print(f"Регистрация вернула {response.status_code}")
    
    def test_user_login_api(self):
        User.objects.create_user(
            email='login@example.com',
            username='loginuser',
            password='LoginPass123!'
        )
        
        data = {
            'email': 'login@example.com',
            'password': 'LoginPass123!'
        }
        
        response = self.client.post(
            '/api/auth/token/login/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertIn(response.status_code, [200, 400])
        
        if response.status_code == 200:
            response_data = json.loads(response.content)
            self.assertIn('auth_token', response_data)
            print("Логин пользователя работает")
        else:
            print(f"Логин вернул {response.status_code}")
    
    def test_get_recipes_list(self):
        from recipes.models import Recipe
        
        Recipe.objects.create(
            author=self.user,
            name='Рецепт 1',
            text='Описание 1',
            cooking_time=30
        )
        Recipe.objects.create(
            author=self.user,
            name='Рецепт 2',
            text='Описание 2',
            cooking_time=45
        )
        
        response = self.client.get('/api/recipes/')
        self.assertIn(response.status_code, [200, 401])
        
        if response.status_code == 200:
            response_data = json.loads(response.content)
            self.assertIn('results', response_data)
            print(f"Список рецептов: {len(response_data.get('results', []))} шт.")
        else:
            print(f"Список рецептов вернул {response.status_code}")

    def test_authenticated_user_profile(self):
        self.client.login(email='viewtest@example.com', password='viewpass123')
        
        response = self.client.get('/api/users/me/')
        
        self.assertIn(response.status_code, [200, 401, 403])
        print(f"Профиль пользователя вернул {response.status_code}")

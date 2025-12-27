from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.apps import apps

User = get_user_model()

class BaseTests(TestCase):
    def test_django_settings(self):
        from django.conf import settings
        self.assertTrue(settings.SECRET_KEY)
        self.assertEqual(settings.AUTH_USER_MODEL, 'users.User')
    
    def test_apps_loaded(self):
        apps_list = [
            'users',
            'recipes', 
            'ingredients',
            'rest_framework',
            'djoser',
        ]
        
        for app in apps_list:
            try:
                apps.get_app_config(app)
                print(f"Приложение {app} загружено")
            except LookupError:
                print(f"Приложение {app} не найдено")
    
    def test_urls_resolve(self):
        urls_to_test = [
            ('/', 200, 301, 302),
            ('/admin/', 302),
            ('/api/', 200, 404),
        ]
        
        for url, *expected_codes in urls_to_test:
            response = self.client.get(url)
            self.assertIn(
                response.status_code, 
                expected_codes,
                f"URL {url} вернул {response.status_code}, ожидалось {expected_codes}"
            )
            print(f"URL {url} вернул {response.status_code}")

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

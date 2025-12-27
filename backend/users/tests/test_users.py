from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class UserBasicTests(TestCase):
    def test_user_str(self):
        user = User.objects.create(
            email='strtest@example.com',
            username='strtest'
        )
        self.assertEqual(str(user), 'strtest@example.com')
    
    def test_user_full_name(self):
        user = User.objects.create(
            email='fullname@example.com',
            username='fullname',
            first_name='Иван',
            last_name='Петров'
        )
        self.assertEqual(user.first_name, 'Иван')
        self.assertEqual(user.last_name, 'Петров')

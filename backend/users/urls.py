from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, EmailAuthTokenView, LogoutView

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')

urlpatterns = [
    path('auth/token/login/', EmailAuthTokenView.as_view(), name='login'),
    path('auth/token/logout/', LogoutView.as_view(), name='logout'),
    path('', include(router.urls)),
]

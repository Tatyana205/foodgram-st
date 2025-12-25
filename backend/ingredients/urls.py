from django.urls import path
from .views import IngredientAPIView

urlpatterns = [
    path('', IngredientAPIView.as_view(), name='ingredients'),
]

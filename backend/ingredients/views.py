from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Ingredient

class IngredientAPIView(APIView):
    def get(self, request):
        name = request.GET.get('name', '')
        
        if name:
            ingredients = Ingredient.objects.filter(
                name__icontains=name
            )[:10]
            
            data = [
                {
                    'id': ing.id,
                    'name': ing.name,
                    'measurement_unit': ing.measurement_unit
                }
                for ing in ingredients
            ]
            return Response(data)
        
        return Response([])

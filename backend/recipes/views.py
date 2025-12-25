from django.shortcuts import get_object_or_404
from django.db.models import Sum
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.pagination import PageNumberPagination 
from django_filters.rest_framework import DjangoFilterBackend

from .models import Recipe, RecipeIngredient, Favorite, ShoppingCart
from .serializers import RecipeSerializer, RecipeCreateSerializer, ShortRecipeSerializer
from .filters import RecipeFilter

class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PageNumberPagination

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeCreateSerializer
        return RecipeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('author').prefetch_related(
            'recipe_ingredients__ingredient'
        )
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user

        try:
            favorite_exists = Favorite.objects.filter(user=user, recipe=recipe).exists()
        except ImportError:
            favorite_exists = user.favorites.filter(id=recipe.id).exists()
        
        if request.method == 'POST':
            if favorite_exists:
                return Response(
                    {'error': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
            try:
                Favorite.objects.create(user=user, recipe=recipe)
            except:
                user.favorites.add(recipe)
        
            return Response(
                {'success': 'Рецепт добавлен в избранное'},
                status=status.HTTP_201_CREATED
            )

        elif request.method == 'DELETE':
            try:
                Favorite.objects.filter(user=user, recipe=recipe).delete()
            except:
                user.favorites.remove(recipe)
        
            return Response(
                {'success': 'Рецепт удален из избранного'},
                status=status.HTTP_200_OK
            )

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        
        if request.method == 'POST':
            cart_item, created = ShoppingCart.objects.get_or_create(
                user=user,
                recipe=recipe
            )
            
            if created:
                cart_recipes = Recipe.objects.filter(shopping_cart__user=user)
                serializer = RecipeSerializer(cart_recipes, many=True, context={'request': request})
                
                return Response({
                    'success': 'Рецепт добавлен в список покупок',
                    'shopping_cart': serializer.data
                }, status=status.HTTP_201_CREATED)
            
            return Response(
                {'error': 'Рецепт уже в списке покупок'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        elif request.method == 'DELETE':
            deleted_count = ShoppingCart.objects.filter(
                user=user, 
                recipe=recipe
            ).delete()[0]
            
            cart_recipes = Recipe.objects.filter(shopping_cart__user=user)
            serializer = RecipeSerializer(cart_recipes, many=True, context={'request': request})
            
            response_data = {
                'success': 'Рецепт удален из списка покупок' if deleted_count else 'Рецепт уже не в списке',
                'shopping_cart': serializer.data,
                'removed_recipe_id': recipe.id
            }
            
            return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount')).order_by('ingredient__name')
        
        if not ingredients:
            return Response(
                {'error': 'Список покупок пуст'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        shopping_list = ["Список покупок:\n"]
        
        for item in ingredients:
            name = item['ingredient__name']
            unit = item['ingredient__measurement_unit']
            amount = item['total_amount']
            shopping_list.append(f" {name} ({unit}) — {amount}\n")
        
        shopping_list.append("\nКонец списка")
        
        response = Response(''.join(shopping_list))
        response['Content-Type'] = 'text/plain; charset=utf-8'
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def favorites(self, request):
        favorite_ids = Favorite.objects.filter(
            user=request.user
        ).values_list('recipe_id', flat=True)
        
        queryset = self.get_queryset().filter(id__in=favorite_ids)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipe = serializer.save(author=request.user)
        
        return Response(
            {
                'id': recipe.id,
                'name': recipe.name,
                'image': request.build_absolute_uri(recipe.image.url) if recipe.image else None,
                'cooking_time': recipe.cooking_time,
                'text': recipe.text,
                'author': {
                    'id': request.user.id,
                    'username': request.user.username,
                    'email': request.user.email
                }
            },
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        
        recipe_url = request.build_absolute_uri(
            f'/recipes/{recipe.id}/'
        )
        
        return Response({
            'short-link': recipe_url,
            'recipe_id': recipe.id,
            'recipe_name': recipe.name
        })

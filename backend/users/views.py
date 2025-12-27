from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, mixins, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import status, parsers

from .models import Subscription
from .serializers import SubscriptionUserSerializer

User = get_user_model()


class EmailAuthTokenView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response(
                {'error': 'Требуется email и пароль'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'Пользователь с таким email не найден'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user.check_password(password):
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                'auth_token': token.key,
            })
        
        return Response(
            {'error': 'Неверный пароль'},
            status=status.HTTP_400_BAD_REQUEST
        )


class UserAvatarView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.JSONParser]

    def delete(self, request):
        user = request.user
        
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
            deleted = True
        else:
            deleted = False
        
        from .serializers import CustomUserSerializer
        serializer = CustomUserSerializer(user, context={'request': request})
        
        return Response({
            'success': True,
            'deleted': deleted,
            'message': 'Аватар удален' if deleted else 'Аватар уже отсутствовал',
            'user': serializer.data
        })
    
    def put(self, request):
        import base64
        from django.core.files.base import ContentFile
        import imghdr
        
        user = request.user
        
        image_data = None
        for field in ['avatar', 'file', 'image']:
            if field in request.data:
                image_data = request.data[field]
                break
        
        if not image_data:
            return Response(
                {'error': 'Изображение не найдено в запросе'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if isinstance(image_data, str) and ';base64,' in image_data:
                format, imgstr = image_data.split(';base64,')
                ext = format.split('/')[-1]
            else:
                imgstr = image_data
                ext = 'jpg'
            
            data = base64.b64decode(imgstr)
            
            image_type = imghdr.what(None, data)
            if not image_type:
                return Response(
                    {'error': 'Неверный формат изображения'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            file = ContentFile(data, name=f'avatar_{user.id}.{image_type}')
            
            if user.avatar:
                user.avatar.delete(save=False)
            
            user.avatar.save(file.name, file)
            user.save()
            
            from .serializers import CustomUserSerializer
            serializer = CustomUserSerializer(user, context={'request': request})
            
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': f'Ошибка обработки изображения: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Token '):
                token_key = auth_header.split(' ')[1]
                from rest_framework.authtoken.models import Token
                token = Token.objects.get(key=token_key)
                token.delete()
                return Response({'success': 'Вы успешно вышли'})
            else:
                return Response(
                    {'error': 'Токен не найден в заголовке'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Token.DoesNotExist:
            return Response(
                {'error': 'Токен не найден'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Ошибка при выходе: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SubscriptionPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    pagination_class = SubscriptionPagination

    permission_classes_by_action = {
        'create': [AllowAny],
        'list': [AllowAny],
        'retrieve': [AllowAny],
        'me': [IsAuthenticated],
        'subscribe': [IsAuthenticated],
        'subscriptions': [IsAuthenticated],
        'set_password': [IsAuthenticated],
        'update': [IsAuthenticated],
        'partial_update': [IsAuthenticated],
        'destroy': [IsAuthenticated],
    }

    def get_serializer_class(self):
        if self.action == 'create':
            from .serializers import UserCreateSerializer
            return UserCreateSerializer
        from .serializers import CustomUserSerializer
        return CustomUserSerializer
    
    def get_permissions(self):
        if self.action in self.permission_classes_by_action:
            return [perm() for perm in self.permission_classes_by_action[self.action]]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        
        if request.method == 'POST':
            if author == request.user:
                return Response(
                    {'error': 'Нельзя подписаться на самого себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if Subscription.objects.filter(user=request.user, author=author).exists():
                return Response(
                    {'error': 'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            Subscription.objects.create(user=request.user, author=author)
            serializer = SubscriptionUserSerializer(author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        elif request.method == 'DELETE':
            subscription = Subscription.objects.filter(
                user=request.user,
                author=author
            ).first()
            
            if not subscription:
                return Response(
                    {'error': 'Вы не подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        subscribed_authors = User.objects.filter(
            following__user=request.user
        )
        
        page = self.paginate_queryset(subscribed_authors)
        if page is not None:
            serializer = SubscriptionUserSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = SubscriptionUserSerializer(
            subscribed_authors, many=True, context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def set_password(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not current_password:
            return Response(
                {'current_password': ['Это поле обязательно.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not new_password:
            return Response(
                {'new_password': ['Это поле обязательно.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not request.user.check_password(current_password):
            return Response(
                {'current_password': ['Текущий пароль неверный.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            validate_password(new_password, request.user)
        except ValidationError as e:
            return Response(
                {'new_password': list(e.messages)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        request.user.set_password(new_password)
        request.user.save()
        
        return Response({'success': 'Пароль успешно изменен'})

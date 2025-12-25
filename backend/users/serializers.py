from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from djoser.serializers import UserSerializer as DjoserUserSerializer
from recipes.models import Recipe

User = get_user_model()

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password]
    )
    
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password']
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }
    
    def validate(self, attrs):
        
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Этот email уже используется."})
        
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({"username": "Этот username уже используется."})
        
        return attrs
    
    def create(self, validated_data):
        user = User.objects.create(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        
        user.set_password(validated_data['password'])
        user.save()
        return user


class CustomUserSerializer(DjoserUserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(required=False, allow_null=True)
    
    class Meta(DjoserUserSerializer.Meta):
        model = User
        fields = DjoserUserSerializer.Meta.fields + ('is_subscribed', 'avatar')
        read_only_fields = ('id', 'email', 'username', 'first_name', 'last_name', 'is_subscribed')
    
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.following.filter(user=request.user).exists()
        return False


class SubscriptionUserSerializer(CustomUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    
    class Meta(CustomUserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + ('recipes', 'recipes_count')
    
    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()
        
        if recipes_limit and recipes_limit.isdigit():
            recipes = recipes[:int(recipes_limit)]
        
        from recipes.serializers import RecipeSerializer
        return RecipeSerializer(recipes, many=True, context={'request': request}).data
    
    def get_recipes_count(self, obj):
        return obj.recipes.count()


class UserAvatarSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField(required=True)
    
    class Meta:
        model = User
        fields = ['avatar']
    
    def update(self, instance, validated_data):
        avatar = validated_data.get('avatar')
        
        if avatar is not None:
            if avatar == '' or avatar is None:
                if instance.avatar:
                    instance.avatar.delete(save=False)
                instance.avatar = None
            else:
                instance.avatar = avatar
        
        instance.save()
        return instance

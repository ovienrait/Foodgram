from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (Favorite, Ingredients, IngredientsRecipes, Recipes,
                            ShoppingCart, Tags)
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from users.models import CustomUser, Subscription


class UserCreateSerializer(BaseUserCreateSerializer):
    """Сериализатор для создания пользователя"""

    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'password')


class UserSerializer(BaseUserSerializer):
    """Сериализатор для пользователя"""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        user = self.context.get('request')
        if not user or user.user.is_anonymous:
            return False
        return Subscription.objects.filter(
            subscription=user.user, subscriber=obj
        ).exists()


class AvatarImageSerializer(UserSerializer):
    """Сериализатор для фотографии пользователя"""

    avatar = Base64ImageField()

    class Meta:
        model = CustomUser
        fields = ('avatar',)


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для краткой информации о рецептах"""

    image = Base64ImageField()

    class Meta:
        model = Recipes
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(UserSerializer):
    """Сериализатор для подписок"""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = Recipes.objects.filter(author=obj.id)
        if limit:
            recipes = recipes[:int(limit)]
        serializer = ShortRecipeSerializer(recipes, many=True, read_only=True)
        return serializer.data

    def get_recipes_count(self, obj):
        return Recipes.objects.filter(author=obj.id).count()


class TagsSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов"""

    class Meta:
        model = Tags
        fields = ('id', 'name', 'slug')


class IngredientsSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов"""

    class Meta:
        model = Ingredients
        fields = ('id', 'name', 'measurement_unit')


class IngredientsRecipesSerializer(serializers.ModelSerializer):
    """Сериализатор для связи ингредиентов и рецептов при GET запросе"""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit')

    class Meta:
        model = IngredientsRecipes
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipesGETSerializer(serializers.ModelSerializer):
    """Сериализатор для рецептов при GET запросе"""

    author = UserSerializer(read_only=True)
    tags = TagsSerializer(many=True, read_only=True)
    ingredients = IngredientsRecipesSerializer(
        many=True, read_only=True, source='ingredientsrecipes')
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    def get_is_favorited(self, obj):
        return (self.context.get(
            'request').user.is_authenticated and Favorite.objects.filter(
                user=self.context.get('request').user, recipe=obj).exists())

    def get_is_in_shopping_cart(self, obj):
        return (self.context.get(
            'request').user.is_authenticated and ShoppingCart.objects.filter(
                user=self.context.get('request').user, recipe=obj).exists())

    class Meta:
        model = Recipes
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time')


class IngredientsRecipesCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для связи ингредиентов при создании рецептов"""

    id = serializers.IntegerField()

    class Meta:
        model = IngredientsRecipes
        fields = ('id', 'amount')


class RecipesCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для рецептов при их создании"""

    author = UserSerializer(read_only=True)
    ingredients = IngredientsRecipesCreateSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tags.objects.all(), many=True)
    image = Base64ImageField(required=True, allow_null=True)

    class Meta:
        model = Recipes
        fields = (
            'ingredients', 'tags', 'image', 'name', 'text',
            'cooking_time', 'author')

    def validate(self, data):
        if not data.get('ingredients'):
            raise ValidationError('Добавьте хотя бы один ингредиент')
        if not data.get('tags'):
            raise ValidationError('Добавьте хотя бы один тег')

        ingredients_list = data['ingredients']
        ingredients = []

        for ingredient in ingredients_list:
            if not Ingredients.objects.filter(id=ingredient['id']).exists():
                raise ValidationError('Такого ингредиента нет')
            ingredients.append(ingredient['id'])
            if ingredients.count(ingredient['id']) > 1:
                raise ValidationError('Нельзя добавить одинаковые ингредиенты')

        tags_list = data['tags']
        tags = []
        for tag in tags_list:
            if tag in tags:
                raise ValidationError('Нельзя добавить одинаковые теги')
            tags.append(tag)
        return data

    def bulk_create_update(self, ingredients, recipe):
        ingredient_list = []
        for ingredient in ingredients:
            ingredient_list.append(IngredientsRecipes(
                recipe=recipe,
                ingredient_id=ingredient.get('id'),
                amount=ingredient.get('amount')))
        IngredientsRecipes.objects.bulk_create(ingredient_list)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipes.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.bulk_create_update(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        instance.tags.clear()
        instance.tags.set(tags)
        ingredients = validated_data.pop('ingredients')
        instance.ingredients.clear()
        self.bulk_create_update(ingredients, instance)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipesGETSerializer(instance, context=self.context).data

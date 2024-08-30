from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import Ingredient, IngredientRecipe, Recipe, Tag
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
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Subscription.objects.filter(
            subscription=obj, subscriber=request.user
        ).exists()


class AvatarImageSerializer(UserSerializer):
    """Сериализатор для фотографии пользователя"""

    avatar = Base64ImageField()

    class Meta:
        model = CustomUser
        fields = ('avatar',)


class ShortRecipeInfoSerializer(serializers.ModelSerializer):
    """Сериализатор для краткой информации о рецептах"""

    image = Base64ImageField()

    class Meta:
        model = Recipe
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
        recipes = obj.recipe.all()
        if self.context.get('recipes_limit'):
            recipes = recipes[:int(self.context.get('recipes_limit'))]
        return ShortRecipeInfoSerializer(
            recipes, many=True, read_only=True).data

    def get_recipes_count(self, obj):
        return obj.recipe.count()


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов"""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов"""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для связи рецептов с соответствующими ингредиентами"""

    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit')

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения рецептов с учетом фильтров"""

    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientRecipeSerializer(
        source='ingredientrecipe', many=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text',
            'cooking_time')

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return obj.favorite.filter(user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return obj.shoppingcart.filter(user=user).exists()


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецепта"""

    ingredients = serializers.ListSerializer(
        child=serializers.DictField(child=serializers.IntegerField()))
    tags = serializers.ListField(child=serializers.IntegerField())
    image = Base64ImageField(required=False)

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'tags', 'image', 'name', 'text', 'cooking_time')

    def validate(self, data):
        if self.instance is None and 'image' not in data:
            raise serializers.ValidationError(
                {"image": "Это поле обязательно."})

        tags = data.get('tags')
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                {'tags': 'Список тегов содержит дублирующиеся значения.'})

        ingredients = data.get('ingredients')
        ingredients_id = list()
        for ingredient in ingredients:
            ingredients_id.append(ingredient.get('id'))
        if len(ingredients_id) != len(set(ingredients_id)):
            raise serializers.ValidationError(
                {'ingredients': 'Список ингредиентов содержит '
                 'дублирующиеся значения.'})

        amount = {
            ingredient['id']: ingredient['amount']
            for ingredient in ingredients}
        ingredient_objects = Ingredient.objects.filter(id__in=amount.keys())
        tag_objects = Tag.objects.filter(id__in=tags)

        if len(ingredient_objects) != len(amount.keys()):
            raise serializers.ValidationError(
                {'ingredients': 'Передан неверный ID ингредиента.'})

        if len(tag_objects) != len(tags):
            raise serializers.ValidationError(
                {'tags': 'Передан неверный ID тега.'})

        data['amount'] = amount
        data['ingredients'] = ingredient_objects
        data['tags'] = tag_objects

        return data

    def save_ingredients_and_tags(self, recipe, ingredients, tags, amount):
        IngredientRecipe.objects.filter(recipe=recipe).delete()
        ingredients_bulk = [
            IngredientRecipe(
                recipe=recipe, ingredient=ingredient,
                amount=amount[ingredient.id]) for ingredient in ingredients]
        IngredientRecipe.objects.bulk_create(ingredients_bulk)

        recipe.tags.set(tags)

    def create(self, validated_data):
        amount = validated_data.pop('amount')
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self.save_ingredients_and_tags(recipe, ingredients, tags, amount)

        return recipe

    def update(self, instance, validated_data):
        amount = validated_data.pop('amount')
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance = super().update(instance, validated_data)
        self.save_ingredients_and_tags(instance, ingredients, tags, amount)

        return instance

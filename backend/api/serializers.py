from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes.models import Ingredients, IngredientsRecipes, Recipes, Tags
from rest_framework import serializers
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


class ShortRecipeInfoSerializer(serializers.ModelSerializer):
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
        recipes = obj.recipes.all()
        if self.context.get('recipes_limit'):
            recipes = recipes[:int(self.context.get('recipes_limit'))]
        return ShortRecipeInfoSerializer(
            recipes, many=True, read_only=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов"""

    class Meta:
        model = Tags
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов"""

    class Meta:
        model = Ingredients
        fields = ('id', 'name', 'measurement_unit')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения рецептов с учетом фильтров"""

    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipes
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text',
            'cooking_time')

    def get_ingredients(self, obj):
        ingredients = IngredientsRecipes.objects.filter(recipe=obj)
        return [
            {
                'id': ingredient.ingredient.id,
                'name': ingredient.ingredient.name,
                'measurement_unit': ingredient.ingredient.measurement_unit,
                'amount': ingredient.amount
            } for ingredient in ingredients]

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
    image = Base64ImageField()

    class Meta:
        model = Recipes
        fields = (
            'ingredients', 'tags', 'image', 'name', 'text', 'cooking_time')

    def validate(self, data):
        fields = ['ingredients', 'tags', 'name', 'text', 'cooking_time']
        for field in fields:
            if field not in data or not data[field]:
                raise serializers.ValidationError(
                    {field: 'Обязательное поле.'})
        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')

        recipe = Recipes.objects.create(**validated_data)

        for ingredient_data in ingredients_data:
            ingredient_id = ingredient_data.get('id')
            amount = ingredient_data.get('amount')
            ingredient = Ingredients.objects.get(id=ingredient_id)
            IngredientsRecipes.objects.create(
                recipe=recipe, ingredient=ingredient, amount=amount)

        for tag_id in tags_data:
            tag = Tags.objects.get(id=tag_id)
            recipe.tags.add(tag)

        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')

        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time)
        image = validated_data.get('image', None)
        if image:
            instance.image = image
        instance.save()

        IngredientsRecipes.objects.filter(recipe=instance).delete()
        for ingredient_data in ingredients_data:
            ingredient_id = ingredient_data.get('id')
            amount = ingredient_data.get('amount')
            try:
                ingredient = Ingredients.objects.get(id=ingredient_id)
            except Ingredients.DoesNotExist:
                raise serializers.ValidationError({
                    'ingredients': f'Ингредиент с id={ingredient_id}'
                    ' не найден.'})
            IngredientsRecipes.objects.create(
                recipe=instance, ingredient=ingredient, amount=amount)

        for tag_id in tags_data:
            try:
                tag = Tags.objects.get(id=tag_id)
            except Tags.DoesNotExist:
                raise serializers.ValidationError({
                    'tags': f'Тег с id={tag_id} не найден.'})
            instance.tags.add(tag)

        return instance

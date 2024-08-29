from django.core.validators import MinValueValidator
from django.db import models

from users.models import CustomUser


class Tag(models.Model):
    """Модель для тегов"""

    name = models.CharField('имя тега', max_length=50)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель для ингредиентов"""

    name = models.CharField(
        'название ингредиента', unique=True, max_length=200)
    measurement_unit = models.CharField('единицы измерения', max_length=50)

    class Meta:
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель для рецептов"""

    ingredients = models.ManyToManyField(
        Ingredient, through='IngredientRecipe')
    tags = models.ManyToManyField(Tag, through='TagRecipe')
    image = models.ImageField('фотография', upload_to='recipes/images/')
    name = models.CharField('название', max_length=50)
    text = models.TextField('описание')
    cooking_time = models.PositiveSmallIntegerField(
        'время приготовления', validators=[MinValueValidator(1)])
    author = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, verbose_name='автор')
    pub_date = models.DateTimeField('дата публикации', auto_now_add=True)

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)
        default_related_name = 'recipe'

    def __str__(self):
        return self.name


class IngredientRecipe(models.Model):
    """Модель для связи ингредиентов и рецептов"""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, verbose_name='название рецепта')
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE,
        verbose_name='название ингредиента')
    amount = models.PositiveSmallIntegerField('количество')

    class Meta:
        verbose_name = 'ингредиент/рецепт'
        verbose_name_plural = 'Ингредиенты/рецепты'
        default_related_name = 'ingredientrecipe'
        constraints = [models.UniqueConstraint(
            fields=['recipe', 'ingredient'], name='unique_ingredient_recipe')]


class TagRecipe(models.Model):
    """Модель для связи тегов и рецептов"""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, verbose_name='название рецепта')
    tag = models.ForeignKey(
        Tag, on_delete=models.CASCADE, verbose_name='тег')

    class Meta:
        verbose_name = 'тег/рецепт'
        verbose_name_plural = 'Теги/рецепты'
        default_related_name = 'tagrecipe'
        constraints = [models.UniqueConstraint(
            fields=['recipe', 'tag'], name='unique_tag_recipe')]


class Favorite(models.Model):
    """Модель для избранных рецептов"""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, verbose_name='название рецепта')
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, verbose_name='имя пользователя')

    class Meta:
        verbose_name = 'избранное'
        verbose_name_plural = 'Список избранного'
        default_related_name = 'favorite'
        constraints = [models.UniqueConstraint(
            fields=['recipe', 'user'], name='unique_user_recipe')]


class ShoppingCart(models.Model):
    """Модель для списка покупок"""

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, verbose_name='название рецепта')
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, verbose_name='имя пользователя')

    class Meta:
        verbose_name = 'покупку'
        verbose_name_plural = 'Списки покупок'
        default_related_name = 'shoppingcart'

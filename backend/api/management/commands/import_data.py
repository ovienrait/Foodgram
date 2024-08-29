import csv
import os

from django.contrib.auth.hashers import make_password
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from recipes.models import (
    Favorite, Ingredient, IngredientRecipe, Recipe,
    ShoppingCart, Tag, TagRecipe)
from users.models import CustomUser, Subscription


class Command(BaseCommand):
    """Команда для импорта данных из CSV файлов по указанной
    директории в определённые модели"""

    def handle(self, *args, **kwargs):
        try:
            directory = os.path.join(
                os.path.dirname(__file__), '../../../data')
            os.chdir(directory)

            self.import_data('users.csv', self.import_users)
            self.import_data('subscriptions.csv', self.import_subscriptions)
            self.import_data('tags.csv', self.import_tags)
            self.import_data('ingredients.csv', self.import_ingredients)
            self.import_data('recipes.csv', self.import_recipes)
            self.import_data('favorites.csv', self.import_favorites)
            self.import_data('shopping_cart.csv', self.import_shoppingcart)

            self.stdout.write(
                self.style.SUCCESS('Импорт данных из CSV файлов завершен.'))

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Произошла ошибка при импорте данных: {e}'))

    def import_data(self, file_name, import_function):
        """Общий метод для импорта данных из CSV файла"""
        with open(
                file_name, mode='r', encoding='utf-8', newline='') as csvfile:
            csv_reader = csv.DictReader(csvfile)
            for row in csv_reader:
                import_function(row)

    def import_users(self, row):
        """Импорт данных в модель CustomUser"""

        password = make_password(row.get('password'))
        avatar_filename = f'avatar_{row.get("id")}.png'
        avatar_path = os.path.join(
            os.path.dirname(__file__),
            '../../../data/images/avatars',
            avatar_filename)
        with open(avatar_path, 'rb') as f:
            avatar = ContentFile(f.read(), name=avatar_filename)
        user, created = CustomUser.objects.get_or_create(
            email=row['email'], username=row['username'],
            first_name=row['first_name'], last_name=row['last_name'],
            password=password, avatar=avatar)
        self.log_result(user, created, 'пользователь')

    def import_subscriptions(self, row):
        """Импорт данных в модель Subscription"""

        for subscription_id in row['subscriptions'].split(','):
            subscription, created = Subscription.objects.get_or_create(
                subscription_id=subscription_id,
                subscriber_id=row['subscriber'])
        self.log_result(
            subscription, created,
            'перечень подписок для пользователя'
            f' {CustomUser.objects.get(id=row["subscriber"]).username}')

    def import_tags(self, row):
        """Импорт данных в модель Tags"""

        tag, created = Tag.objects.get_or_create(
            name=row['name'], slug=row['slug'])
        self.log_result(tag, created, 'тег')

    def import_ingredients(self, row):
        """Импорт данных в модель Ingredients"""

        ingredient, created = Ingredient.objects.get_or_create(
            name=row['name'], measurement_unit=row['measurement_unit'])
        self.log_result(ingredient, created, 'ингредиент')

    def import_recipes(self, row):
        """Импорт данных в модель Recipes"""

        image_filename = f'recipe_{row.get("id")}.png'
        image_path = os.path.join(
            os.path.dirname(__file__),
            '../../../data/images/recipes',
            image_filename)
        with open(image_path, 'rb') as f:
            image = ContentFile(f.read(), name=image_filename)
        recipe, created = Recipe.objects.get_or_create(
            image=image, name=row['name'], text=row['text'],
            cooking_time=row['cooking_time'],
            author=CustomUser.objects.get(id=row['author']))
        ingredients_list = row['ingredients'].split(',')
        for ingredient_info in ingredients_list:
            ingredient_id, amount = ingredient_info.split(':')
            ingredient = Ingredient.objects.get(id=ingredient_id)
            IngredientRecipe.objects.get_or_create(
                recipe=recipe, ingredient=ingredient, amount=amount)
        for tag_id in row['tags'].split(','):
            tag = Tag.objects.get(id=tag_id)
            TagRecipe.objects.get_or_create(recipe=recipe, tag=tag)
        self.log_result(recipe, created, 'рецепт')

    def import_favorites(self, row):
        """Импорт данных в модель Favorite"""

        for recipe_id in row['recipes'].split(','):
            favorite, created = Favorite.objects.get_or_create(
                recipe_id=recipe_id, user_id=row['user'])
        self.log_result(
            favorite, created,
            'перечень рецептов в избранное для пользователя'
            f' {CustomUser.objects.get(id=row["user"]).username}')

    def import_shoppingcart(self, row):
        """Импорт данных в модель ShoppingCart"""

        for recipe_id in row['recipes'].split(','):
            shopping_cart, created = ShoppingCart.objects.get_or_create(
                recipe_id=recipe_id, user_id=row['user'])
        self.log_result(
            shopping_cart, created,
            'список покупок для пользователя'
            f' {CustomUser.objects.get(id=row["user"]).username}')

    def log_result(self, obj, created, model_name):
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Добавлен {model_name} "{obj}"'))
        else:
            self.stdout.write(
                f'{model_name.capitalize()} "{obj}" уже существует!')

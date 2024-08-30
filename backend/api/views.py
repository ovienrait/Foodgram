from collections import defaultdict
from io import BytesIO

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.pagination import (
    LimitOffsetPagination, PageNumberPagination)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from recipes.models import (
    Favorite, Ingredient, IngredientRecipe, Recipe,
    ShoppingCart, Tag)
from users.models import CustomUser, Subscription
from .serializers import (
    AvatarImageSerializer, IngredientSerializer,
    RecipeCreateUpdateSerializer, RecipeSerializer,
    ShortRecipeInfoSerializer, SubscriptionSerializer,
    TagSerializer, UserSerializer)


class CustomUserViewSet(UserViewSet):
    """Обработчик для пользователей"""

    serializer_class = UserSerializer
    pagination_class = LimitOffsetPagination

    def get_permissions(self):
        if self.action in ('list', 'create', 'retrieve'):
            self.permission_classes = [AllowAny, ]
        return super().get_permissions()


class AvatarView(APIView):
    """Обработчик для добавления и удаления аватара"""

    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = AvatarImageSerializer(
            request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request):
        request.user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriptionListView(APIView):
    """Обработчик для получения перечня подписок"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = CustomUser.objects.filter(subscription__subscriber=user)
        paginator = PageNumberPagination()
        paginator.page_size = request.query_params.get('limit', 6)
        result_page = paginator.paginate_queryset(queryset, request)
        recipes_limit = request.query_params.get('recipes_limit')
        serializer = SubscriptionSerializer(
            result_page, many=True,
            context={'request': request, 'recipes_limit': recipes_limit})
        return paginator.get_paginated_response(serializer.data)


class SubscribeButtonView(APIView):
    """Обработчик для функции подписки и отписки"""

    permission_classes = [IsAuthenticated]

    def get_user_or_404(self, id):
        """Возвращает пользователя или вызывает ошибку 404"""
        try:
            return CustomUser.objects.get(id=id)
        except CustomUser.DoesNotExist:
            raise NotFound(detail='Пользователь не найден.')

    def post(self, request, id):
        """Подписаться на пользователя"""

        subscriber = request.user
        subscription = self.get_user_or_404(id)

        if subscriber == subscription:
            return Response(
                {'detail': 'Нельзя подписаться на самого себя.'},
                status=status.HTTP_400_BAD_REQUEST)
        if Subscription.objects.filter(
            subscriber=subscriber, subscription=subscription
        ).exists():
            return Response(
                {'detail': 'Вы уже подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST)
        Subscription.objects.create(
            subscriber=subscriber, subscription=subscription)
        recipes_limit = request.query_params.get('recipes_limit')
        serializer = SubscriptionSerializer(
            subscription,
            context={'request': request, 'recipes_limit': recipes_limit})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, id):
        """Отписаться от пользователя"""

        subscriber = request.user
        subscription = self.get_user_or_404(id)

        current_subscription = Subscription.objects.filter(
            subscriber=subscriber, subscription=subscription
        ).first()
        if not current_subscription:
            return Response(
                {'detail': 'Вы не подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST)
        current_subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagListView(APIView):
    """Обработчик для получения списка тегов"""

    def get(self, request):
        tags = Tag.objects.all()
        return Response(TagSerializer(tags, many=True).data)


class TagDetailView(APIView):
    """Обработчик для получения тега по ID"""

    def get(self, request, id):
        try:
            tag = Tag.objects.get(pk=id)
        except Tag.DoesNotExist:
            return Response(
                {'detail': 'Тег не найден.'},
                status=status.HTTP_404_NOT_FOUND)
        return Response(TagSerializer(tag).data)


class IngredientListView(APIView):
    """Обработчик для получения списка ингредиентов"""

    def get(self, request):
        ingredients = Ingredient.objects.all()
        search_query = request.query_params.get('name')
        if search_query:
            ingredients = ingredients.filter(name__istartswith=search_query)
        return Response(
            IngredientSerializer(ingredients, many=True).data)


class IngredientDetailView(APIView):
    """Обработчик для получения информации об ингредиенте по ID"""

    def get(self, request, id):
        try:
            ingredient = Ingredient.objects.get(pk=id)
        except Ingredient.DoesNotExist:
            return Response(
                {'detail': 'Ингредиент не найден.'},
                status=status.HTTP_404_NOT_FOUND)
        return Response(IngredientSerializer(ingredient).data)


class RecipeListView(APIView):
    """Обработчик для получения списка рецептов с фильтрацией
    и создания нового рецепта"""

    def get(self, request):
        """Получение списка рецептов"""

        recipes = Recipe.objects.all()

        is_favorited = request.query_params.get('is_favorited')
        if is_favorited == '1' and request.user.is_authenticated:
            recipes = recipes.filter(favorite__user=request.user)

        is_in_shopping_cart = request.query_params.get('is_in_shopping_cart')
        if is_in_shopping_cart == '1' and request.user.is_authenticated:
            recipes = recipes.filter(shoppingcart__user=request.user)

        author = request.query_params.get('author')
        if author:
            recipes = recipes.filter(author__id=author)

        tags = request.query_params.getlist('tags')
        if tags:
            recipes = recipes.filter(tags__slug__in=tags).distinct()

        paginator = PageNumberPagination()
        paginator.page_size = request.query_params.get('limit', 6)
        paginated_recipes = paginator.paginate_queryset(recipes, request)

        return paginator.get_paginated_response(RecipeSerializer(
            paginated_recipes, many=True, context={'request': request}).data)

    def post(self, request):
        """Создание нового рецепта"""

        self.permission_classes = [IsAuthenticated]
        self.check_permissions(request)

        serializer = RecipeCreateUpdateSerializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        recipe = serializer.save(author=request.user)
        serializer = RecipeSerializer(recipe, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RecipeDetailView(APIView):
    """Обработчик для получения информации о рецепте по ID,
    а также для изменения и удаления рецепта"""

    def get_recipe_or_404(self, id):
        """Возвращает рецепт или вызывает ошибку 404"""
        try:
            return Recipe.objects.get(pk=id)
        except Recipe.DoesNotExist:
            raise NotFound(detail='Рецепт не найден.')

    def get(self, request, id):
        """Получение информации о рецепте по ID"""

        recipe = self.get_recipe_or_404(id)
        return Response(
            RecipeSerializer(recipe, context={'request': request}).data)

    def patch(self, request, id):
        """Изменение рецепта"""

        recipe = self.get_recipe_or_404(id)

        if recipe.author != request.user:
            return Response(
                {'detail': 'У вас нет прав на изменение этого рецепта.'},
                status=status.HTTP_403_FORBIDDEN)

        serializer = RecipeCreateUpdateSerializer(
            recipe, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        recipe = serializer.save()
        return Response(RecipeSerializer(
            recipe, context={'request': request}).data)

    def delete(self, request, id):
        """Удаление рецепта"""

        recipe = get_object_or_404(Recipe, id=id)

        if recipe.author != request.user:
            return Response(
                {'detail': 'У вас нет прав на удаление этого рецепта.'},
                status=status.HTTP_403_FORBIDDEN)

        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()


class RecipeGetShortLinkView(APIView):
    """Обработчик для получения короткой ссылки на рецепт"""

    def get(self, request, id):
        recipe = get_object_or_404(Recipe, id=id)

        base_url = request.build_absolute_uri('/') + 's/'
        short_link = f"{base_url}{recipe.id}"

        return Response({"short-link": short_link}, status=status.HTTP_200_OK)


class ShortLinkRedirectView(APIView):
    """Обработчик для редиректа по короткой ссылке"""

    def get(self, request, short_hash):
        recipe = get_object_or_404(Recipe, id=short_hash)
        return HttpResponseRedirect(f'/recipes/{recipe.id}/')


class BaseRecipeActionView(APIView):
    """Базовый класс для добавления и удаления рецептов
    из избранного и списка покупок"""

    permission_classes = [IsAuthenticated]

    def get_message(self):
        return 'действие выполнено'

    def post(self, request, id):
        """Добавление рецепта"""

        recipe = get_object_or_404(Recipe, id=id)
        user = request.user

        if self.model.objects.filter(user=user, recipe=recipe).exists():
            return Response(
                {'detail': f'Этот рецепт уже {self.get_message()}.'},
                status=status.HTTP_400_BAD_REQUEST)

        self.model.objects.create(user=user, recipe=recipe)
        return Response(
            ShortRecipeInfoSerializer(recipe).data,
            status=status.HTTP_201_CREATED)

    def delete(self, request, id):
        """Удаление рецепта"""

        recipe = get_object_or_404(Recipe, id=id)
        user = request.user

        instance = self.model.objects.filter(user=user, recipe=recipe).first()
        if not instance:
            return Response(
                {'detail': f'Этот рецепт отсутствует {self.get_message()}.'},
                status=status.HTTP_400_BAD_REQUEST)

        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FavoriteRecipeView(BaseRecipeActionView):
    """Обработчик для добавления и удаления рецептов из избранного"""

    model = Favorite

    def get_message(self):
        return 'в избранном'


class ShoppingCartRecipeView(BaseRecipeActionView):
    """Обработчик для добавления и удаления рецептов из списка покупок"""

    model = ShoppingCart

    def get_message(self):
        return 'в списке покупок'


class DownloadShoppingCartView(APIView):
    """Обработчик для скачивания списка покупок в формате PDF"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        recipes = ShoppingCart.objects.filter(
            user=user).values_list('recipe')
        ingredients_query = IngredientRecipe.objects.filter(
            recipe__in=recipes).select_related('ingredient')

        ingredient_data = defaultdict(lambda: {'quantity': 0, 'unit': ''})

        for entry in ingredients_query:
            ingredient = entry.ingredient
            ingredient_name = ingredient_data[ingredient.name]
            ingredient_name['quantity'] += entry.amount
            ingredient_name['unit'] = ingredient.measurement_unit

        ingredients = sorted([
            (name, data['quantity'], data['unit'])
            for name, data in ingredient_data.items()], key=lambda x: x[0])

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        font_path = settings.BASE_DIR / 'data/font/DejaVuSans.ttf'
        pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
        p.setFont('DejaVuSans', 12)

        p.setFont('DejaVuSans', 16)
        p.drawString(100, height - 60, 'Список покупок:')

        p.setFont('DejaVuSans', 12)
        y = height - 100
        line_height = 20
        margin_bottom = 40

        for ingredient in ingredients:
            name, quantity, unit = ingredient
            line = f'{name} — {quantity} {unit}'
            p.drawString(100, y, line)
            y -= line_height

            if y < margin_bottom:
                p.showPage()
                p.setFont('DejaVuSans', 12)
                y = height - 60

        p.showPage()
        p.save()

        buffer.seek(0)
        pdf = buffer.getvalue()
        buffer.close()

        filename = 'shopping_list.pdf'
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

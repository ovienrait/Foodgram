import hashlib
from collections import defaultdict
from io import BytesIO

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredients, IngredientsRecipes, Recipes,
                            ShoppingCart, Tags)
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import status
from rest_framework.pagination import (LimitOffsetPagination,
                                       PageNumberPagination)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import CustomUser, Subscription

from .serializers import (AvatarImageSerializer, IngredientSerializer,
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
        if request.data:
            serializer = AvatarImageSerializer(
                request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(status=status.HTTP_400_BAD_REQUEST)

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

    def post(self, request, id):
        """Подписаться на пользователя"""

        subscriber = request.user
        try:
            subscription = CustomUser.objects.get(id=id)
        except CustomUser.DoesNotExist:
            return Response(
                {'detail': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND)
        if subscriber == subscription:
            return Response(
                {'detail': 'Нельзя подписаться на самого себя'},
                status=status.HTTP_400_BAD_REQUEST)
        if Subscription.objects.filter(
            subscriber=subscriber, subscription=subscription
        ).exists():
            return Response(
                {'detail': 'Вы уже подписаны на этого пользователя'},
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
        try:
            subscription = CustomUser.objects.get(id=id)
        except CustomUser.DoesNotExist:
            return Response(
                {'detail': 'Пользователь не найден'},
                status=status.HTTP_404_NOT_FOUND)
        current_subscription = Subscription.objects.filter(
            subscriber=subscriber, subscription=subscription
        ).first()
        if not current_subscription:
            return Response(
                {'detail': 'Вы не подписаны на этого пользователя'},
                status=status.HTTP_400_BAD_REQUEST)
        current_subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagsListView(APIView):
    """Обработчик для получения списка тегов"""

    def get(self, request):
        tags = Tags.objects.all()
        return Response(TagSerializer(tags, many=True).data)


class TagDetailView(APIView):
    """Обработчик для получения тега по ID"""

    def get(self, request, id):
        try:
            tag = Tags.objects.get(pk=id)
        except Tags.DoesNotExist:
            return Response(
                {'detail': 'Тег не найден'},
                status=status.HTTP_404_NOT_FOUND)
        return Response(TagSerializer(tag).data)


class IngredientsListView(APIView):
    """Обработчик для получения списка ингредиентов"""

    def get(self, request):
        ingredients = Ingredients.objects.all()
        search_query = request.query_params.get('name')
        if search_query:
            ingredients = ingredients.filter(name__istartswith=search_query)
        return Response(
            IngredientSerializer(ingredients, many=True).data)


class IngredientDetailView(APIView):
    """Обработчик для получения информации об ингредиенте по ID"""

    def get(self, request, id):
        try:
            ingredient = Ingredients.objects.get(pk=id)
        except Ingredients.DoesNotExist:
            return Response(
                {'detail': 'Ингредиент не найден'},
                status=status.HTTP_404_NOT_FOUND)
        return Response(IngredientSerializer(ingredient).data)


class RecipesListView(APIView):
    """Обработчик для получения списка рецептов с фильтрацией
    и создания нового рецепта"""

    def get(self, request):
        """Получение списка рецептов"""

        recipes = Recipes.objects.all()

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
        if serializer.is_valid():
            recipe = serializer.save(author=request.user)
            serializer = RecipeSerializer(recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecipeDetailView(APIView):
    """Обработчик для получения информации о рецепте по ID,
    а также для изменения и удаления рецепта"""

    def get(self, request, id):
        """Получение информации о рецепте по ID"""

        try:
            recipe = Recipes.objects.get(pk=id)
        except Recipes.DoesNotExist:
            return Response(
                {'detail': 'Рецепт не найден'},
                status=status.HTTP_404_NOT_FOUND)
        return Response(
            RecipeSerializer(recipe, context={'request': request}).data)

    def patch(self, request, id):
        """Изменение рецепта"""

        try:
            recipe = Recipes.objects.get(pk=id)
        except Recipes.DoesNotExist:
            return Response(
                {'detail': 'Рецепт не найден'},
                status=status.HTTP_404_NOT_FOUND)

        if recipe.author != request.user:
            return Response(
                {'detail': 'У вас нет прав на изменение этого рецепта'},
                status=status.HTTP_403_FORBIDDEN)

        serializer = RecipeCreateUpdateSerializer(
            recipe, data=request.data, partial=True,
            context={'request': request})
        if serializer.is_valid():
            recipe = serializer.save()
            return Response(RecipeSerializer(
                recipe, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        """Удаление рецепта"""

        recipe = get_object_or_404(Recipes, id=id)

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
        recipe = get_object_or_404(Recipes, id=id)

        base_url = request.build_absolute_uri('/') + 's/'
        unique_str = f"{recipe.id}-{recipe.name}"
        short_hash = hashlib.md5(unique_str.encode()).hexdigest()[:3]
        short_link = f"{base_url}{short_hash}"

        return Response({"short-link": short_link}, status=status.HTTP_200_OK)


class ShortLinkRedirectView(APIView):
    """Обработчик для редиректа по короткой ссылке"""

    def get(self, request, short_hash):
        all_recipes = Recipes.objects.all()
        for recipe in all_recipes:
            unique_str = f"{recipe.id}-{recipe.name}"
            computed_hash = hashlib.md5(unique_str.encode()).hexdigest()[:3]
            if computed_hash == short_hash:
                return HttpResponseRedirect(f'/api/recipes/{recipe.id}/')


class BaseRecipeActionView(APIView):
    """Базовый класс для добавления и удаления рецептов
    из избранного и списка покупок"""

    permission_classes = [IsAuthenticated]

    def get_message(self):
        return 'действие выполнено'

    def post(self, request, id):
        """Добавление рецепта"""

        recipe = get_object_or_404(Recipes, id=id)
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

        recipe = get_object_or_404(Recipes, id=id)
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
        ingredients_query = IngredientsRecipes.objects.filter(
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
        for ingredient in ingredients:
            name, quantity, unit = ingredient
            line = f'{name} — {quantity} {unit}'
            p.drawString(100, y, line)
            y -= 20

        p.showPage()
        p.save()

        buffer.seek(0)
        pdf = buffer.getvalue()
        buffer.close()

        filename = 'shopping_list.pdf'
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

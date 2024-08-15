from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import baseconv
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet

from users.models import CustomUser, Subscription
from recipes.models import (
    Tags, Ingredients, Recipes, Favorite, ShoppingCart, IngredientsRecipes)
from .filters import RecipesFilter
from .pagination import RecipesPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    AvatarImageSerializer, UserSerializer, SubscriptionSerializer,
    TagsSerializer, IngredientsSerializer, RecipesCreateSerializer,
    RecipesGETSerializer, ShortRecipeSerializer)


class CustomUserViewSet(UserViewSet):
    """Обработчик для пользователей"""

    serializer_class = UserSerializer
    pagination_class = LimitOffsetPagination

    def get_permissions(self):
        if self.action in ('list', 'create', 'retrieve'):
            self.permission_classes = [AllowAny, ]
        return super().get_permissions()

    @action(
        detail=False, methods=['PUT', 'DELETE'],
        permission_classes=(IsAuthenticated,), url_path='me/avatar',
        serializer_class=AvatarImageSerializer,)
    def avatar(self, request):
        if request.method == 'PUT':
            if request.data:
                serializer = self.get_serializer(
                    request.user, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            self.request.user.avatar.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=['post', 'delete'],
        permission_classes=(IsAuthenticated,))
    def subscribe(self, request, id):
        subscription = request.user
        subscriber = get_object_or_404(CustomUser, id=id)
        if request.method == 'POST':
            if Subscription.objects.filter(
                subscription=subscription, subscriber=subscriber
            ).exists():
                return Response(
                    'Вы уже подписаны на этого автора',
                    status=status.HTTP_400_BAD_REQUEST)
            if subscriber == subscription:
                return Response(
                    'Нельзя подписаться на самого себя',
                    status=status.HTTP_400_BAD_REQUEST)
            serializer = SubscriptionSerializer(
                subscriber, context={"request": request, })
            Subscription.objects.create(
                subscription=subscription, subscriber=subscriber)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if not Subscription.objects.filter(
            subscription=subscription, subscriber=subscriber
        ).exists():
            return Response(
                'Подписка не найдена', status=status.HTTP_400_BAD_REQUEST)
        subscribe = get_object_or_404(
            Subscription, subscription=subscription, subscriber=subscriber)
        subscribe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False, methods=['get', ],
        permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        user = request.user
        queryset = CustomUser.objects.filter(subscriber__subscription=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(
            pages, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
    """Обработчик для тегов"""

    queryset = Tags.objects.all()
    serializer_class = TagsSerializer
    pagination_class = None


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    """Обработчик для ингредиентов"""

    queryset = Ingredients.objects.all()
    serializer_class = IngredientsSerializer
    pagination_class = None
    filter_backends = (filters.SearchFilter,)
    filterset_fields = ('name',)
    search_fields = ('^name',)


class RecipesViewSet(viewsets.ModelViewSet):
    """Обработчик для рецептов"""

    queryset = Recipes.objects.all()
    pagination_class = RecipesPagination
    permission_classes = (IsAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = RecipesFilter
    search_fields = ('tags',)

    def get_serializer_class(self):
        if self.action == 'create' or self.action == 'partial_update':
            return RecipesCreateSerializer
        return RecipesGETSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def add_or_delete(self, model, pk, message, request):
        user = request.user
        recipe = get_object_or_404(Recipes, id=pk)
        related_recipe = model.objects.filter(user=user, recipe=recipe)

        if request.method == 'POST':
            if related_recipe.exists():
                return Response(message, status=status.HTTP_400_BAD_REQUEST)
            model.objects.create(user=user, recipe=recipe)
            serializer = ShortRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if related_recipe.exists():
            related_recipe.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True, methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,))
    def favorite(self, request, pk):
        """Добавление рецепта в избранное"""

        return self.add_or_delete(
            Favorite, pk, 'Рецепт уже есть в избранном', request)

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk):
        """Добавление ингредиентов в список покупок"""

        return self.add_or_delete(
            ShoppingCart, pk, 'Ингредиенты уже добавлены', request)

    @action(
        detail=False, methods=['get'],
        permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request):
        user = request.user
        recipes = ShoppingCart.objects.filter(user=user).values_list('recipe')
        ingredients = (IngredientsRecipes.objects.filter(
            recipe__in=recipes).values('ingredient').annotate(
                quantity=Sum('amount')).values_list(
                    'ingredient__name', 'quantity',
                    'ingredient__measurement_unit'))
        shopping_list = []
        for ingredient in ingredients:
            name, value, unit = ingredient
            shopping_list.append(f'{name}, {value} {unit}')
        shopping_list = '\n'.join(shopping_list)
        filename = 'Shopping_list.txt'
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'],
            url_path='get-link', url_name='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        encode_id = baseconv.base64.encode(recipe.id)
        short_link = request.build_absolute_uri(
            reverse('shortlink', kwargs={'encoded_id': encode_id}))
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)


class ShortLinkView(APIView):
    """Обработчик для коротких ссылок"""

    def get(self, request, encoded_id):
        if not set(encoded_id).issubset(set(baseconv.BASE64_ALPHABET)):
            return Response(
                {'error': 'Недопустимые символы в короткой ссылке'},
                status=status.HTTP_400_BAD_REQUEST)
        recipe_id = baseconv.base64.decode(encoded_id)
        return redirect(f'/recipes/{recipe_id}/',)

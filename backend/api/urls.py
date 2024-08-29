from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AvatarView, CustomUserViewSet, DownloadShoppingCartView,
    FavoriteRecipeView, IngredientDetailView, IngredientListView,
    RecipeDetailView, RecipeGetShortLinkView, RecipeListView,
    ShoppingCartRecipeView, SubscribeButtonView,
    SubscriptionListView, TagDetailView, TagListView)

app_name = 'api'

router = DefaultRouter()
router.register(r'users', CustomUserViewSet, basename='users')

urlpatterns = [
    path('users/me/avatar/', AvatarView.as_view(), name='avatar'),
    path(
        'users/subscriptions/', SubscriptionListView.as_view(),
        name='subscriptions'),
    path(
        'users/<int:id>/subscribe/', SubscribeButtonView.as_view(),
        name='subscribe'),
    path('tags/', TagListView.as_view(), name='tags'),
    path('tags/<int:id>/', TagDetailView.as_view(), name='tag'),
    path('ingredients/', IngredientListView.as_view(), name='ingredients'),
    path(
        'ingredients/<int:id>/', IngredientDetailView.as_view(),
        name='ingredient'),
    path('recipes/', RecipeListView.as_view(), name='recipes'),
    path('recipes/<int:id>/', RecipeDetailView.as_view(), name='recipe'),
    path('recipes/<int:id>/get-link/', RecipeGetShortLinkView.as_view(),
         name='get_short_link'),
    path('recipes/<int:id>/favorite/', FavoriteRecipeView.as_view(),
         name='favorite'),
    path('recipes/<int:id>/shopping_cart/', ShoppingCartRecipeView.as_view(),
         name='shopping_cart'),
    path('recipes/download_shopping_cart/', DownloadShoppingCartView.as_view(),
         name='download_shopping_cart_pdf'),
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]

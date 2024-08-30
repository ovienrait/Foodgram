from django.contrib import admin

from .models import (
    Favorite, Ingredient, IngredientRecipe, Recipe,
    ShoppingCart, Tag, TagRecipe)


@admin.register(Tag)
class TagsAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    list_filter = ('name',)


@admin.register(Ingredient)
class IngredientsAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('name',)


class IngredientsRecipesInline(admin.TabularInline):
    model = IngredientRecipe
    extra = 0


@admin.register(Recipe)
class RecipesAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'text', 'cooking_time', 'image', 'author', 'display_tags',
        'display_ingredients', 'display_favorite')
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    inlines = [IngredientsRecipesInline, ]

    def display_tags(self, obj):
        tags = obj.tags.values_list('name', flat=True)
        return ', '.join(tags)

    display_tags.short_description = 'Теги'

    def display_ingredients(self, obj):
        ingredients = obj.ingredients.values_list('name', flat=True)
        return ', '.join(ingredients)

    display_ingredients.short_description = 'Ингредиенты'

    def display_favorite(self, obj):
        return obj.favorite.count()

    display_favorite.short_description = (
        'Количество добавлений в избранное')


@admin.register(IngredientRecipe)
class IngredientsRecipesAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe', 'ingredient')
    list_filter = ('recipe', 'ingredient')


@admin.register(TagRecipe)
class TagsRecipesAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'tag')
    search_fields = ('recipe', 'tag')
    list_filter = ('recipe', 'tag')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user')
    search_fields = ('recipe', 'user')
    list_filter = ('recipe', 'user')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user')
    search_fields = ('recipe', 'user')
    list_filter = ('recipe', 'user')

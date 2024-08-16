from django.contrib import admin

from .models import (Favorite, Ingredients, IngredientsRecipes, Recipes,
                     ShoppingCart, Tags, TagsRecipes)


@admin.register(Tags)
class TagsAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    list_filter = ('name',)


@admin.register(Ingredients)
class IngredientsAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('name',)


class IngredientsRecipesInline(admin.TabularInline):
    model = IngredientsRecipes
    extra = 1


@admin.register(Recipes)
class RecipesAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'text', 'author', 'cooking_time', 'image',
        'display_tags', 'display_ingredients',
        'display_recipe_favorite', 'pub_date')
    search_fields = ('name', 'author__email')
    list_filter = ('tags',)
    inlines = [IngredientsRecipesInline, ]

    def display_recipe_favorite(self, obj):
        count = Favorite.objects.filter(recipe=obj).count()
        return count

    display_recipe_favorite.short_description = (
        'Количесво добавлений в избранное')

    def display_tags(self, obj):
        return ', '.join([str(item) for item in obj.tags.all()])

    display_tags.short_description = 'Теги'

    def display_ingredients(self, obj):
        return ', '.join([str(item) for item in obj.ingredients.all()])

    display_ingredients.short_description = 'Ингредиенты'


@admin.register(IngredientsRecipes)
class IngredientsRecipesAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe', 'ingredient')
    list_filter = ('recipe', 'ingredient')


@admin.register(TagsRecipes)
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

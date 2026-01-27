from django.contrib import admin
from .models import (
    User, UserProfile,
    Ingredient, UserPantry,
    Recipe, RecipeIngredient, RecipeStep,
    RecommendationHistory,
)

admin.site.register(User)
admin.site.register(UserProfile)
admin.site.register(Ingredient)
admin.site.register(UserPantry)
admin.site.register(Recipe)
admin.site.register(RecipeIngredient)
admin.site.register(RecipeStep)
admin.site.register(RecommendationHistory)

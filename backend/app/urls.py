from django.urls import path
from .views import (
    ProfileView,
    PantryView,
    PantryItemDeleteView,
    PantryItemUpdateView,
    RecipeRecommendationView,
    RecipeActionView,
    RecommendationHistoryView,
    RecommendationConversionView,
    RecipeSaveView,
    RecipeUnsaveView,
    SavedRecipesView,
    ExternalRecipeSearchView,
    ExternalRecipeSeedView,
    AdminStatusView,
    UserRecipeListCreateView,
    UserRecipeDestroyView,
    RecipeDetailView,
    RecipeSearchView,
    AdminRecipeDebugView,
    TossLoginView,
    AuthStatusView,
    AuthLogoutView,
    DemoLoginView,
)



urlpatterns = [
    path("profile/", ProfileView.as_view()),
    path("pantry/", PantryView.as_view()),
    path("pantry/<int:item_id>/", PantryItemDeleteView.as_view()),
    path("pantry/<int:item_id>/update/", PantryItemUpdateView.as_view()),
    path("recommendations/recipes/", RecipeRecommendationView.as_view()),
    path("recipes/action/", RecipeActionView.as_view()),
    path("recommendations/history/", RecommendationHistoryView.as_view()),
    path("recommendations/conversion/", RecommendationConversionView.as_view()),
    path("recipes/save/", RecipeSaveView.as_view()),
    path("recipes/unsave/", RecipeUnsaveView.as_view()),
    path("recipes/saved/", SavedRecipesView.as_view()),
    path("external/recipes/", ExternalRecipeSearchView.as_view()),
    path("external/recipes/seed/", ExternalRecipeSeedView.as_view()),
    path("admin/status/", AdminStatusView.as_view()),
    path("admin/recipe-debug/", AdminRecipeDebugView.as_view()),
    path("recipes/user/", UserRecipeListCreateView.as_view()),
    path("recipes/user/<int:pk>/", UserRecipeDestroyView.as_view()),
    path("recipes/search/", RecipeSearchView.as_view()),
    path("recipes/<int:pk>/", RecipeDetailView.as_view()),
    # 인증
    path("auth/toss/login/", TossLoginView.as_view()),
    path("auth/demo/login/", DemoLoginView.as_view()),  # 발표용 데모 로그인
    path("auth/status/", AuthStatusView.as_view()),
    path("auth/logout/", AuthLogoutView.as_view()),
]


from rest_framework import serializers
from .models import UserProfile, UserPantry, Recipe, RecommendationHistory, RecipeStep

class UserPantrySerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(
        source='ingredient.name_ko', read_only=True
    )

    class Meta:
        model = UserPantry
        fields = ['id', 'ingredient_name', 'quantity_text', 'expires_at']

class PantryCreateSerializer(serializers.Serializer):
    ingredient_name = serializers.CharField()
    quantity_text = serializers.CharField(required=False, allow_blank=True, default="")
    expires_at = serializers.DateField(required=False, allow_null=True)

class PantryUpdateSerializer(serializers.Serializer):
    quantity_text = serializers.CharField(required=False, allow_blank=True)
    expires_at = serializers.DateField(required=False, allow_null=True)

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "diet_type",
            "allergies",
            "spice_level",
            "max_cook_time_min",
            "skill_level",
            "servings_default",
        ]


class RecipeRecommendationSerializer(serializers.Serializer):
    recipe_id = serializers.IntegerField()
    title = serializers.CharField()
    cook_time_min = serializers.IntegerField(allow_null=True)
    coverage = serializers.FloatField()
    missing_count = serializers.IntegerField()
    missing_ingredients = serializers.ListField(child=serializers.CharField())
    shopping_list = serializers.ListField(child=serializers.CharField())
    reasons = serializers.ListField(child=serializers.CharField())
    saved = serializers.BooleanField(required=False)
    score = serializers.FloatField()
    debug = serializers.JSONField(required=False)

    
class RecipeActionCreateSerializer(serializers.Serializer):
    recipe_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=["save", "cook", "skip"])


class RecommendationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationHistory
        fields = [
            "id",
            "created_at",
            "context",
            "result_recipe_ids",
        ]


class RecipeMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ["id", "title", "cook_time_min"]


class RecommendationHistoryDetailSerializer(serializers.ModelSerializer):
    recipes = serializers.SerializerMethodField()

    class Meta:
        model = RecommendationHistory
        fields = ["id", "created_at", "context", "result_recipe_ids", "recipes"]

    def get_recipes(self, obj):
        ids = obj.result_recipe_ids or []
        qs = Recipe.objects.filter(id__in=ids)
        # ids 순서 유지
        by_id = {r.id: r for r in qs}
        ordered = [by_id[i] for i in ids if i in by_id]
        return RecipeMiniSerializer(ordered, many=True).data

class SavedRecipeListSerializer(serializers.Serializer):
    recipe_id = serializers.IntegerField(source="recipe.id")
    title = serializers.CharField(source="recipe.title")
    cook_time_min = serializers.IntegerField(source="recipe.cook_time_min", allow_null=True)
    saved_at = serializers.DateTimeField(source="created_at")

class UserRecipeListSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ["id", "title", "cook_time_min", "image_url", "thumbnail_url", "is_public", "created_at"]

    def get_thumbnail_url(self, obj):
        """업로드된 썸네일이 있으면 해당 URL, 없으면 image_url 반환"""
        request = self.context.get("request")
        if obj.thumbnail:
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return obj.image_url or None

class StepInputSerializer(serializers.Serializer):
    step_no = serializers.IntegerField()
    description = serializers.CharField()
    image_url = serializers.CharField(required=False, allow_blank=True, default="")


class UserRecipeCreateSerializer(serializers.Serializer):
    title = serializers.CharField()
    cook_time_min = serializers.IntegerField(required=False, allow_null=True)
    ingredients = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False
    )
    image_url = serializers.URLField(required=False, allow_blank=True)
    is_public = serializers.BooleanField(required=False, default=True)
    steps = serializers.ListField(
        child=StepInputSerializer(),
        required=False,
        allow_empty=True,
        default=list
    )

class RecipeStepSerializer(serializers.ModelSerializer):
    step_image_url = serializers.SerializerMethodField()

    class Meta:
        model = RecipeStep
        fields = ["step_no", "description", "image_url", "step_image_url"]

    def get_step_image_url(self, obj):
        """업로드된 이미지가 있으면 해당 URL, 없으면 image_url 반환"""
        request = self.context.get("request")
        if obj.image:
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return obj.image_url or None

class RecipeDetailSerializer(serializers.ModelSerializer):
    steps = RecipeStepSerializer(many=True, read_only=True)

    class Meta:
        model = Recipe
        fields = [
            "id",
            "title",
            "summary",
            "image_url",
            "image_url_small",
            "cook_time_min",
            "raw_ingredients",
            "steps",
            "source",
            "source_recipe_id",
            "external_source",
            "external_id",
        ]


class RecipeSearchSerializer(serializers.ModelSerializer):
    recipe_id = serializers.IntegerField(source="id")

    class Meta:
        model = Recipe
        fields = ["recipe_id", "title", "cook_time_min", "image_url"]
from django.db import models


class User(models.Model):
    # App in Toss 연동 대비: 토스에서 내려오는 사용자 식별자(나중에 채움)
    toss_user_id = models.CharField(max_length=128, blank=True, null=True, unique=True)
    nickname = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nickname or f"user:{self.id}"


class UserProfile(models.Model):
    class DietType(models.TextChoices):
        NONE = "NONE", "NONE"
        LOW_CARB = "LOW_CARB", "LOW_CARB"
        LOW_SODIUM = "LOW_SODIUM", "LOW_SODIUM"
        HIGH_PROTEIN = "HIGH_PROTEIN", "HIGH_PROTEIN"
        VEGAN = "VEGAN", "VEGAN"

    class SkillLevel(models.TextChoices):
        BEGINNER = "BEGINNER", "BEGINNER"
        MID = "MID", "MID"
        PRO = "PRO", "PRO"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    diet_type = models.CharField(max_length=20, choices=DietType.choices, default=DietType.NONE)
    allergies = models.JSONField(default=list, blank=True)   # ["peanut", ...]
    spice_level = models.IntegerField(default=0)             # 0~3
    max_cook_time_min = models.IntegerField(default=20)
    skill_level = models.CharField(max_length=20, choices=SkillLevel.choices, default=SkillLevel.BEGINNER)
    servings_default = models.IntegerField(default=1)

    def __str__(self):
        return f"profile:{self.user_id}"


class Ingredient(models.Model):
    class Category(models.TextChoices):
        MEAT = "MEAT", "MEAT"
        VEG = "VEG", "VEG"
        DAIRY = "DAIRY", "DAIRY"
        SAUCE = "SAUCE", "SAUCE"
        ETC = "ETC", "ETC"

    name_ko = models.CharField(max_length=100, unique=True)
    name_en = models.CharField(max_length=100, blank=True, null=True)
    synonyms = models.JSONField(default=list, blank=True)  # ["파", "쪽파"]
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.ETC)

    def __str__(self):
        return self.name_ko


class UserPantry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pantry_items")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="in_pantries")
    quantity_text = models.CharField(max_length=50, blank=True, default="")
    expires_at = models.DateField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "ingredient")]  # 같은 재료 중복 등록 방지

    def __str__(self):
        return f"{self.user_id}:{self.ingredient.name_ko}"


class Recipe(models.Model):
    class Difficulty(models.TextChoices):
        EASY = "EASY", "EASY"
        MID = "MID", "MID"
        HARD = "HARD", "HARD"

    # 출처
    source = models.CharField(max_length=50, default="PUBLIC")  # MFDS / PUBLIC / ETC
    source_recipe_id = models.CharField(max_length=100, blank=True, default="")
    is_public = models.BooleanField(default=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="created_recipes")

    # 외부 API 자산화용
    external_source = models.CharField(max_length=30, blank=True, default="")  # ex) "foodsafety"
    external_id = models.CharField(max_length=100, blank=True, default="", db_index=True)

    # 기본 정보
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True, default="")
    image_url = models.URLField(blank=True, default="")
    # 사용자 업로드 썸네일 (ImageField)
    thumbnail = models.ImageField(upload_to="recipes/thumbnails/", blank=True, null=True)
    # 조리법/외부 원문
    image_url_small = models.URLField(blank=True, default="")   # ATT_FILE_NO_MK
    raw_ingredients = models.TextField(blank=True, default="")  # RCP_PARTS_DTLS

    instructions = models.JSONField(default=list, blank=True)        # ["1단계", "2단계"...]
    instruction_images = models.JSONField(default=list, blank=True)  # ["url1", "url2"...]

    cook_time_min = models.IntegerField(blank=True, null=True)

    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        default=Difficulty.EASY
    )

    servings = models.IntegerField(blank=True, null=True)
    cuisine = models.CharField(max_length=50, blank=True, default="")
    tags = models.JSONField(default=list, blank=True)  # ["혼밥","간단"]

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["external_source", "external_id"]),
        ]
        constraints = [
            # external_source + external_id 조합이 비어있지 않을 때만 유니크 제약
            models.UniqueConstraint(
                fields=["external_source", "external_id"],
                name="unique_external_recipe",
                condition=models.Q(external_source__gt="") & models.Q(external_id__gt=""),
            ),
        ]

    def __str__(self):
        return self.title

class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_ingredients")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="ingredient_recipes")
    amount_text = models.CharField(max_length=50, blank=True, default="")
    is_optional = models.BooleanField(default=False)

    class Meta:
        unique_together = [("recipe", "ingredient")]

    def __str__(self):
        return f"{self.recipe_id}:{self.ingredient.name_ko}"


class RecipeStep(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="steps")
    step_no = models.IntegerField()
    description = models.TextField()
    image_url = models.URLField(blank=True, default="")
    # 사용자 업로드 이미지 (ImageField)
    image = models.ImageField(upload_to="recipes/steps/", blank=True, null=True)

    class Meta:
        unique_together = [("recipe", "step_no")]
        ordering = ["step_no"]

    def __str__(self):
        return f"{self.recipe_id}:step{self.step_no}"


class RecommendationHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recommendation_history")
    context = models.JSONField(default=dict, blank=True)
    result_recipe_ids = models.JSONField(default=list, blank=True)  # [101, 12, 33]
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"rec:{self.user_id}:{self.created_at}"

class RecipeAction(models.Model):
    ACTION_CHOICES = [
        ("save", "save"),
        ("cook", "cook"),
        ("skip", "skip"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recipe_actions")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="actions")
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "action", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.recipe_id}:{self.action}"

class UserSavedRecipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "recipe")]

    def __str__(self):
        return f"{self.user_id}-{self.recipe_id}"

class ExternalRecipeCache(models.Model):
    provider = models.CharField(max_length=50)  # "foodsafety"
    cache_key = models.CharField(max_length=200, unique=True)  # ex) "recipes:name=계란:start=1:end=50"
    payload = models.JSONField()
    fetched_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.provider}:{self.cache_key}"

class AppSetting(models.Model):
    key = models.CharField(max_length=50, unique=True)
    value = models.CharField(max_length=200, blank=True, default="")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key}={self.value}"


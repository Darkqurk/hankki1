from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta

from app.models import Ingredient, Recipe, RecipeIngredient, UserPantry
from app.utils import get_or_create_test_user


class Command(BaseCommand):
    help = "Seed demo data for hankki (ingredients, recipes, recipe ingredients, pantry)"

    @transaction.atomic
    def handle(self, *args, **options):
        user = get_or_create_test_user()

        # Ingredients
        egg, _ = Ingredient.objects.get_or_create(name_ko="계란")
        scallion, _ = Ingredient.objects.get_or_create(name_ko="대파")
        salt, _ = Ingredient.objects.get_or_create(name_ko="소금")
        soy, _ = Ingredient.objects.get_or_create(name_ko="간장")
        garlic, _ = Ingredient.objects.get_or_create(name_ko="마늘")

        # Recipes
        r1, _ = Recipe.objects.get_or_create(
            title="초간단 계란국",
            defaults={"cook_time_min": 15},
        )
        r2, _ = Recipe.objects.get_or_create(
            title="간장계란밥",
            defaults={"cook_time_min": 10},
        )
        r3, _ = Recipe.objects.get_or_create(
            title="계란찜",
            defaults={"cook_time_min": 12},
        )

        # Recipe Ingredients (필수/선택: 너 모델은 is_optional)
        # 초간단 계란국: 계란(필수), 소금(필수), 대파(선택), 마늘(선택)
        RecipeIngredient.objects.get_or_create(recipe=r1, ingredient=egg, defaults={"is_optional": False, "amount_text": "2개"})
        RecipeIngredient.objects.get_or_create(recipe=r1, ingredient=salt, defaults={"is_optional": False, "amount_text": "약간"})
        RecipeIngredient.objects.get_or_create(recipe=r1, ingredient=scallion, defaults={"is_optional": True, "amount_text": "조금"})
        RecipeIngredient.objects.get_or_create(recipe=r1, ingredient=garlic, defaults={"is_optional": True, "amount_text": "1톨"})

        # 간장계란밥: 계란(필수), 간장(필수)
        RecipeIngredient.objects.get_or_create(recipe=r2, ingredient=egg, defaults={"is_optional": False, "amount_text": "1~2개"})
        RecipeIngredient.objects.get_or_create(recipe=r2, ingredient=soy, defaults={"is_optional": False, "amount_text": "1T"})

        # 계란찜: 계란(필수), 소금(필수), 대파(선택)
        RecipeIngredient.objects.get_or_create(recipe=r3, ingredient=egg, defaults={"is_optional": False, "amount_text": "2개"})
        RecipeIngredient.objects.get_or_create(recipe=r3, ingredient=salt, defaults={"is_optional": False, "amount_text": "약간"})
        RecipeIngredient.objects.get_or_create(recipe=r3, ingredient=scallion, defaults={"is_optional": True, "amount_text": "조금"})

        # Pantry (유저 냉장고): 계란은 임박(보너스 확인용), 소금 보유
        UserPantry.objects.get_or_create(
            user=user,
            ingredient=egg,
            defaults={"quantity_text": "6개", "expires_at": date.today() + timedelta(days=1)},
        )
        UserPantry.objects.get_or_create(
            user=user,
            ingredient=salt,
            defaults={"quantity_text": "1통", "expires_at": None},
        )

        self.stdout.write(self.style.SUCCESS("✅ Demo seed complete. Try GET /api/recommendations/recipes/?top=10"))

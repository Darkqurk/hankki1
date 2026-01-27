from django.db import transaction
from .foodsafety import get_foodsafety_recipes
from .seed_foodsafety import seed_from_foodsafety_rows
from app.utils import recommend_recipes_for_user, get_or_create_test_user
from ..models import Recipe


class RecommendationService:

    @staticmethod
    def get_recommendations(user, top=5):
        """
        서비스 레벨 추천 함수
        - 내부 추천 우선
        - 비어있으면 외부 API seed 후 재추천
        """
        results = recommend_recipes_for_user(user, top=top)

        if results:
            return results, 200

        # 내부 DB 비어있으면 외부에서 seed 시도
        seeded = RecommendationService.seed_external()

        if seeded:
            results = recommend_recipes_for_user(user, top=top)
            return results, 201

        return [], 503

    @staticmethod
    @transaction.atomic
    def seed_external(limit=30):
        """
        외부 API에서 데이터 받아 DB 저장
        """
        try:
            payload = get_foodsafety_recipes(1, limit)
            rows = payload.get("COOKRCP01", {}).get("row", [])
            return len(rows) > 0
        except Exception:
            return False

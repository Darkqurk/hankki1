from rest_framework.views import APIView
from datetime import date, timedelta
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import RetrieveAPIView, ListCreateAPIView, DestroyAPIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from .models import  User, UserProfile, UserPantry, Ingredient, RecommendationHistory, RecipeAction, Recipe,  UserSavedRecipe, RecipeIngredient, RecipeStep
from django.db import transaction
from .serializers import UserProfileSerializer, UserPantrySerializer, PantryCreateSerializer, PantryUpdateSerializer, RecipeRecommendationSerializer, RecipeActionCreateSerializer, RecommendationHistoryDetailSerializer, SavedRecipeListSerializer, UserRecipeCreateSerializer, RecipeDetailSerializer, UserRecipeListSerializer, RecipeSearchSerializer
import json
from .utils import (
    get_or_create_test_user,
    recommend_recipes_for_user,
    get_demo_user,
    score_single_recipe_for_user,
    get_current_user,
    toss_generate_token,
    toss_get_user_info,
    get_or_create_user_by_toss_id,
)
from app.services.recipe_source import get_foodsafety_recipes
from app.services.seed_foodsafety import seed_from_foodsafety_rows
from .services.recipe_source import get_foodsafety_recipes
from .services.seed_foodsafety import seed_from_foodsafety_rows
from .services.recommendation_service import RecommendationService
from django.utils.timezone import now
from django.core.cache import cache
import hashlib
import json

class PantryListView(APIView):
    def get(self, request):
        # MVP: 임시로 user_id=1 사용
        qs = UserPantry.objects.filter(user_id=1)
        serializer = UserPantrySerializer(qs, many=True)
        return Response(serializer.data)

class PantryView(APIView):
    def get(self, request):
        user = get_or_create_test_user()
        qs = UserPantry.objects.filter(user=user).select_related("ingredient")
        return Response(UserPantrySerializer(qs, many=True).data)

    def post(self, request):
        user = get_or_create_test_user()
        serializer = PantryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 재료명 → Ingredient 찾아서 연결 (없으면 생성)
        ingredient, _ = Ingredient.objects.get_or_create(name_ko=data["ingredient_name"])

        item, _ = UserPantry.objects.update_or_create(
            user=user,
            ingredient=ingredient,
            defaults={
                "quantity_text": data.get("quantity_text", ""),
                "expires_at": data.get("expires_at", None),
            },
        )
        return Response(UserPantrySerializer(item).data, status=status.HTTP_201_CREATED)

class PantryItemDeleteView(APIView):
    def delete(self, request, item_id: int):
        user = get_or_create_test_user()
        UserPantry.objects.filter(user=user, id=item_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class PantryItemUpdateView(APIView):
    def patch(self, request, item_id: int):
        user = get_or_create_test_user()
        item = UserPantry.objects.get(user=user, id=item_id)

        serializer = PantryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "quantity_text" in data:
            item.quantity_text = data["quantity_text"]
        if "expires_at" in data:
            item.expires_at = data["expires_at"]

        item.save()
        return Response(UserPantrySerializer(item).data, status=200)

class ProfileView(APIView):
    def get(self, request):
        user = get_or_create_test_user()
        profile = user.profile
        return Response(UserProfileSerializer(profile).data)

    def put(self, request):
        user = get_or_create_test_user()
        profile = user.profile
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class RecipeRecommendationView(APIView):
    def get(self, request):
        user = get_or_create_test_user()

        try:
            top = int(request.query_params.get("top", 5))
        except ValueError:
            top = 5

        # ===== 1) 냉장고 상태 기반 캐시 키 생성 =====
        pantry_rows = list(
            UserPantry.objects.filter(user=user)
            .values("ingredient_id", "quantity_text", "expires_at")
            .order_by("ingredient_id")
        )

        fingerprint = hashlib.md5(
            json.dumps(pantry_rows, default=str).encode()
        ).hexdigest()

        cache_key = f"reco:v1:user:{user.id}:top:{top}:fp:{fingerprint}"

        # ===== 2) 캐시 HIT =====
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=200)

        # ===== 3) 캐시 MISS → 서비스 호출 =====
        data, status_code = RecommendationService.get_recommendations(user, top)

        payload = RecipeRecommendationSerializer(data, many=True).data

        # ===== 4) 캐시 저장 =====
        cache.set(cache_key, payload, timeout=120)  # 2분

        return Response(payload, status=status_code)
    
class RecipeActionView(APIView):
    def post(self, request):
        user = get_or_create_test_user()
        s = RecipeActionCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        recipe_id = s.validated_data["recipe_id"]
        action = s.validated_data["action"]

        recipe = Recipe.objects.get(id=recipe_id)
        RecipeAction.objects.create(user=user, recipe=recipe, action=action)

        # 추천 캐시 무효화 (cook/skip 반영이 즉시 보이도록)
        self._invalidate_recommendation_cache(user)

        return Response({"ok": True}, status=201)

    def _invalidate_recommendation_cache(self, user):
        """해당 사용자의 추천 캐시 삭제"""
        for top in [3, 5, 10, 20]:
            pantry_rows = list(
                UserPantry.objects.filter(user=user)
                .values("ingredient_id", "quantity_text", "expires_at")
                .order_by("ingredient_id")
            )
            fingerprint = hashlib.md5(
                json.dumps(pantry_rows, default=str).encode()
            ).hexdigest()
            cache_key = f"reco:v1:user:{user.id}:top:{top}:fp:{fingerprint}"
            cache.delete(cache_key)

class RecommendationHistoryView(APIView):
    def get(self, request):
        user = get_or_create_test_user()
        qs = RecommendationHistory.objects.filter(user=user).order_by("-created_at")[:20]
        return Response(RecommendationHistoryDetailSerializer(qs, many=True).data)

class RecommendationConversionView(APIView):
    def get(self, request):
        user = get_or_create_test_user()

        days = request.query_params.get("days", "7")
        try:
            days_n = int(days)
        except ValueError:
            days_n = 7

        cutoff = date.today() - timedelta(days=days_n)

        # 최근 추천 로그
        histories = RecommendationHistory.objects.filter(
            user=user, created_at__date__gte=cutoff
        )

        recommended_ids = set()
        for h in histories:
            for rid in (h.result_recipe_ids or []):
                recommended_ids.add(rid)

        if not recommended_ids:
            return Response(
                {
                    "window_days": days_n,
                    "recommended_count": 0,
                    "converted_count": 0,
                    "conversion_rate": 0.0,
                }
            )

        # 추천된 레시피 중 실제 행동(cook/save) 발생
        converted_ids = set(
            RecipeAction.objects.filter(
                user=user,
                recipe_id__in=recommended_ids,
                action__in=["cook", "save"],
                created_at__date__gte=cutoff,
            ).values_list("recipe_id", flat=True)
        )

        recommended_count = len(recommended_ids)
        converted_count = len(converted_ids)

        conversion_rate = (
            converted_count / recommended_count
            if recommended_count > 0
            else 0.0
        )

        return Response(
            {
                "window_days": days_n,
                "recommended_count": recommended_count,
                "converted_count": converted_count,
                "conversion_rate": round(conversion_rate, 3),
            }
        )

# 저장    
class RecipeSaveView(APIView):
    def post(self, request):
        user = get_or_create_test_user()
        recipe_id = request.data.get("recipe_id")

        if not recipe_id:
            return Response({"detail": "recipe_id required"}, status=400)

        recipe = Recipe.objects.get(id=recipe_id)
        UserSavedRecipe.objects.get_or_create(user=user, recipe=recipe)

        # 추천 캐시 무효화 (저장된 레시피가 추천에서 즉시 제외되도록)
        self._invalidate_recommendation_cache(user)

        return Response({"status": "saved"}, status=201)

    def _invalidate_recommendation_cache(self, user):
        """해당 사용자의 추천 캐시 삭제"""
        cache_pattern = f"reco:v1:user:{user.id}:*"
        # Django 기본 캐시는 패턴 삭제 미지원이므로 delete_many 사용
        # 모든 top 값에 대해 캐시 삭제
        for top in [3, 5, 10, 20]:
            pantry_rows = list(
                UserPantry.objects.filter(user=user)
                .values("ingredient_id", "quantity_text", "expires_at")
                .order_by("ingredient_id")
            )
            fingerprint = hashlib.md5(
                json.dumps(pantry_rows, default=str).encode()
            ).hexdigest()
            cache_key = f"reco:v1:user:{user.id}:top:{top}:fp:{fingerprint}"
            cache.delete(cache_key)

# 저장해제
class RecipeUnsaveView(APIView):
    def post(self, request):
        user = get_or_create_test_user()
        recipe_id = request.data.get("recipe_id")

        UserSavedRecipe.objects.filter(user=user, recipe_id=recipe_id).delete()

        # 추천 캐시 무효화 (저장 해제된 레시피가 추천에 다시 나타나도록)
        self._invalidate_recommendation_cache(user)

        return Response({"status": "unsaved"}, status=200)

    def _invalidate_recommendation_cache(self, user):
        """해당 사용자의 추천 캐시 삭제"""
        for top in [3, 5, 10, 20]:
            pantry_rows = list(
                UserPantry.objects.filter(user=user)
                .values("ingredient_id", "quantity_text", "expires_at")
                .order_by("ingredient_id")
            )
            fingerprint = hashlib.md5(
                json.dumps(pantry_rows, default=str).encode()
            ).hexdigest()
            cache_key = f"reco:v1:user:{user.id}:top:{top}:fp:{fingerprint}"
            cache.delete(cache_key)

class SavedRecipesView(APIView):
    def get(self, request):
        user = get_or_create_test_user()

        qs = (
            UserSavedRecipe.objects
            .filter(user=user)
            .select_related("recipe")
            .order_by("-created_at")
        )
        return Response(SavedRecipeListSerializer(qs, many=True).data)
    
class ExternalRecipeSearchView(APIView):
    def get(self, request):
        query = request.query_params.get("query", "")
        return Response({"ok": True, "query": query})


class ExternalRecipeSeedView(APIView):
    """
    관리자/개발자용: 외부 레시피를 우리 DB에 적재(seed)
    """
    def post(self, request):
        limit = int(request.data.get("limit", 20))
        q = (request.data.get("query") or "").strip() or None

        payload = get_foodsafety_recipes(start=1, end=max(20, limit), name_query=q)
        rows = payload.get("COOKRCP01", {}).get("row", [])

        result = seed_from_foodsafety_rows(rows, limit=limit)
        return Response(
            {"ok": True, "limit": limit, "query": q, **result},
            status=status.HTTP_201_CREATED,
        )
    
class ExternalRecipeSeedView(APIView):
    def post(self, request):
        limit = int(request.data.get("limit", 20))
        query = (request.data.get("query") or "").strip() or None

        payload = get_foodsafety_recipes(start=1, end=max(20, limit), name_query=query)
        rows = payload.get("COOKRCP01", {}).get("row", []) or []

        result = seed_from_foodsafety_rows(rows, limit=limit)
        return Response(
            {"ok": True, "limit": limit, "query": query, **result},
            status=status.HTTP_201_CREATED,
        )
    

class AdminStatusView(APIView):
    def get(self, request):
        return Response({
            "recipes_total": Recipe.objects.count(),
            "last_seed": RecommendationHistory.objects.order_by("-created_at")
                .values_list("created_at", flat=True)
                .first(),
            "users": User.objects.count(),
            "pantry_items": UserPantry.objects.count(),
            "server_time": now()
        })
    
class UserRecipeListCreateView(APIView):
    """
    GET: 내 레시피 목록
    POST: 내 레시피 생성 (multipart/form-data 지원)
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        user = get_current_user(request)
        qs = Recipe.objects.filter(source="USER", user=user)

        # 검색 파라미터 처리
        q = request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(title__icontains=q)

        qs = qs.order_by("-created_at")
        serializer = UserRecipeListSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request):
        user = get_current_user(request)

        # FormData에서 필드 추출
        title = request.data.get("title", "").strip()
        cook_time_min = request.data.get("cook_time_min")
        ingredients_raw = request.data.get("ingredients", "")
        is_public = request.data.get("is_public", "true")
        steps_json = request.data.get("steps_json", "[]")

        # 유효성 검사
        if not title:
            return Response({"detail": "title is required"}, status=400)

        # cook_time_min 파싱
        try:
            cook_time_min = int(cook_time_min) if cook_time_min else None
        except (ValueError, TypeError):
            cook_time_min = None

        # ingredients 파싱 (콤마 구분 문자열 또는 리스트)
        if isinstance(ingredients_raw, str):
            ingredients = [i.strip() for i in ingredients_raw.split(",") if i.strip()]
        elif isinstance(ingredients_raw, list):
            ingredients = [i.strip() for i in ingredients_raw if i.strip()]
        else:
            ingredients = []

        if not ingredients:
            return Response({"detail": "ingredients is required"}, status=400)

        # is_public 파싱
        if isinstance(is_public, str):
            is_public = is_public.lower() in ("true", "1", "yes")

        # steps 파싱 (JSON 문자열)
        try:
            steps_data = json.loads(steps_json) if steps_json else []
        except json.JSONDecodeError:
            steps_data = []

        # 썸네일 파일 처리
        thumbnail_file = request.FILES.get("thumbnail")

        # 레시피 생성
        recipe = Recipe.objects.create(
            user=user,
            title=title,
            cook_time_min=cook_time_min,
            source="USER",
            source_recipe_id=f"user_{user.id}_{title[:50]}",
            is_public=is_public,
            thumbnail=thumbnail_file,  # ImageField
        )

        # 재료 저장
        for name in ingredients:
            if not name:
                continue
            ing, _ = Ingredient.objects.get_or_create(name_ko=name)
            RecipeIngredient.objects.get_or_create(
                recipe=recipe,
                ingredient=ing,
                defaults={"amount_text": "", "is_optional": False},
            )

        # 조리 단계 저장
        for idx, step in enumerate(steps_data):
            step_no = step.get("step_no", idx + 1)
            description = step.get("description", "").strip()
            if not description:
                continue

            # 단계별 이미지 파일 (step_image_0, step_image_1, ...)
            step_image_file = request.FILES.get(f"step_image_{idx}")

            RecipeStep.objects.create(
                recipe=recipe,
                step_no=step_no,
                description=description,
                image=step_image_file,  # ImageField
            )

        # 응답
        result = UserRecipeListSerializer(recipe, context={"request": request}).data
        return Response(result, status=201)

class UserRecipeDestroyView(DestroyAPIView):
    queryset = Recipe.objects.all() # Used for lookup_field, but actual filtering is in get_object
    lookup_field = 'pk'

    def get_object(self):
        user = get_or_create_test_user()
        pk = self.kwargs['pk']
        obj = get_object_or_404(
            self.get_queryset(), pk=pk, user=user, source="USER"
        )
        return obj

class RecipeDetailView(RetrieveAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeDetailSerializer


class RecipeSearchView(APIView):
    """레시피 제목 검색 (공개 레시피 + 내 레시피)"""

    def get(self, request):
        user = get_or_create_test_user()
        q = request.query_params.get("q", "").strip()

        if not q:
            return Response([])

        # 공개 레시피 OR 내 레시피
        from django.db.models import Q
        qs = Recipe.objects.filter(
            Q(is_public=True) | Q(user=user)
        ).filter(title__icontains=q).order_by("-created_at")[:20]

        return Response(RecipeSearchSerializer(qs, many=True).data)


class AdminRecipeDebugView(APIView):
    """
    관리자 디버그: 특정 레시피의 추천 점수/디버그 정보를 demo 유저 기준으로 반환.
    GET /api/admin/recipe-debug/?recipe_id=85&demo_user=1
    """

    def get(self, request):
        recipe_id = request.query_params.get("recipe_id")
        demo_user_num = request.query_params.get("demo_user", "1")

        if not recipe_id:
            return Response(
                {"error": "recipe_id 파라미터가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            recipe_id = int(recipe_id)
        except (ValueError, TypeError):
            return Response(
                {"error": "recipe_id는 정수여야 합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = get_demo_user(demo_user_num)
        result = score_single_recipe_for_user(user, recipe_id, exclude_saved=False)

        if result is None:
            return Response(
                {"error": "해당 레시피를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(result)


class TossLoginView(APIView):
    """
    토스 인앱 로그인 처리
    POST /api/auth/toss/login/

    입력: { "authorizationCode": "...", "referrer": "..." }
    처리:
      1. generate-token API 호출 → accessToken
      2. login-me API 호출 → userKey
      3. User get_or_create(toss_user_id=userKey)
      4. 세션에 user_id 저장
    응답: { "ok": true, "toss_user_id": "..." }
    """

    def post(self, request):
        authorization_code = request.data.get("authorizationCode")
        referrer = request.data.get("referrer")

        if not authorization_code:
            return Response(
                {"ok": False, "error": "authorizationCode is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not referrer:
            return Response(
                {"ok": False, "error": "referrer is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # 1) 토스 OAuth 토큰 발급
            token_data = toss_generate_token(authorization_code, referrer)
            access_token = token_data.get("accessToken")

            if not access_token:
                return Response(
                    {"ok": False, "error": "Failed to get accessToken from Toss"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            # 2) 토스 유저 정보 조회
            user_info = toss_get_user_info(access_token)
            user_key = user_info.get("userKey")

            if not user_key:
                return Response(
                    {"ok": False, "error": "Failed to get userKey from Toss"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            # 3) 우리 DB에 유저 생성/조회
            user = get_or_create_user_by_toss_id(str(user_key))

            # 4) 세션에 user_id 저장
            request.session["user_id"] = user.id
            request.session.save()

            return Response({
                "ok": True,
                "toss_user_id": user.toss_user_id,
                "user_id": user.id,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"ok": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AuthLogoutView(APIView):
    """
    로그아웃 (세션 삭제)
    POST /api/auth/logout/
    """

    def post(self, request):
        request.session.flush()
        return Response({"ok": True})


# =============================================
# 발표용 데모 로그인 (Admin 화이트리스트 포함)
# =============================================

# Admin 권한을 가진 toss_user_id 화이트리스트
ADMIN_USER_IDS = {"demo_admin", "test_user_1"}


class DemoLoginView(APIView):
    """
    발표용 데모 로그인
    POST /api/auth/demo/login/
    body: { "demo_user": "user" | "admin" }

    - demo_user="user" → 일반 사용자 (demo_user_1)
    - demo_user="admin" → 관리자 (demo_admin)
    """

    def post(self, request):
        demo_type = request.data.get("demo_user", "user")

        if demo_type == "admin":
            toss_user_id = "demo_admin"
            nickname = "관리자(데모)"
        else:
            toss_user_id = "demo_user_1"
            nickname = "사용자(데모)"

        # User get_or_create
        user, created = User.objects.get_or_create(
            toss_user_id=toss_user_id,
            defaults={"nickname": nickname},
        )
        UserProfile.objects.get_or_create(user=user)

        # 세션에 저장
        request.session["user_id"] = user.id

        return Response({
            "ok": True,
            "user_id": user.id,
            "toss_user_id": user.toss_user_id,
            "nickname": user.nickname,
            "is_admin": toss_user_id in ADMIN_USER_IDS,
        })


class AuthStatusView(APIView):
    """
    현재 로그인 상태 확인 (Admin 여부 포함)
    GET /api/auth/status/
    """

    def get(self, request):
        user_id = request.session.get("user_id")

        if not user_id:
            return Response({
                "logged_in": False,
                "toss_user_id": None,
                "user_id": None,
                "nickname": None,
                "is_admin": False,
            })

        try:
            user = User.objects.get(id=user_id)
            return Response({
                "logged_in": True,
                "toss_user_id": user.toss_user_id,
                "user_id": user.id,
                "nickname": user.nickname,
                "is_admin": user.toss_user_id in ADMIN_USER_IDS,
            })
        except User.DoesNotExist:
            request.session.flush()
            return Response({
                "logged_in": False,
                "toss_user_id": None,
                "user_id": None,
                "nickname": None,
                "is_admin": False,
            })
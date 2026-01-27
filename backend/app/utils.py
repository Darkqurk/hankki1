from datetime import date, timedelta
from django.utils import timezone
from math import exp
from django.db.models import Prefetch, Count
from django.utils import timezone
from .models import (
    User,
    UserProfile,
    UserPantry,
    Recipe,
    RecipeIngredient,
    RecipeAction,
    RecommendationHistory,
    UserSavedRecipe,
)
import hashlib
import json
import re

# =============================================
# 재료 표준화: 동의어 사전 + 정규화 함수
# =============================================

SYNONYM_MAP = {
    # 계란 계열
    "달걀": "계란",
    "전란": "계란",
    "계란흰자": "계란",
    "계란노른자": "계란",
    "달걀흰자": "계란",
    "달걀노른자": "계란",
    "흰자": "계란",
    "노른자": "계란",
    # 파 계열
    "대파": "파",
    "쪽파": "파",
    "실파": "파",
    # 설탕 계열
    "슈가": "설탕",
    "백설탕": "설탕",
    "황설탕": "설탕",
    # 간장 계열
    "진간장": "간장",
    "국간장": "간장",
    "양조간장": "간장",
    # 고추 계열
    "청양고추": "고추",
    "홍고추": "고추",
    "풋고추": "고추",
    # 마늘 계열
    "다진마늘": "마늘",
    "마늘쫑": "마늘",
    # 양파 계열
    "적양파": "양파",
    # 고기 계열
    "돼지고기": "돼지",
    "돼지앞다리": "돼지",
    "돼지목살": "돼지",
    "돼지삼겹": "돼지",
    "삼겹살": "돼지",
    "소고기": "소",
    "쇠고기": "소",
    "닭고기": "닭",
    "닭가슴살": "닭",
    "닭다리": "닭",
}


def normalize_ingredient(s: str) -> str:
    """
    재료명 정규화:
    1. 앞뒤 공백 제거 + 소문자
    2. 괄호 내용 제거: "당근(1/2개)" → "당근"
    3. 숫자 제거
    4. 특수문자 제거 (한글/영문만 남기기)
    5. 공백 제거
    6. 동의어 사전 적용
    """
    if not s:
        return ""

    text = s.strip().lower()

    # 괄호 내용 제거: (xxx), [xxx]
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)

    # 숫자 제거
    text = re.sub(r'\d+', '', text)

    # 한글, 영문만 남기기 (특수문자, 공백 제거)
    text = re.sub(r'[^가-힣a-zA-Z]', '', text)

    # 동의어 사전 적용
    if text in SYNONYM_MAP:
        text = SYNONYM_MAP[text]

    return text

def get_or_create_test_user():
    """
    테스트용 유저/프로필 확보
    (토스 로그인 붙기 전 임시 유저)
    """
    user, _ = User.objects.get_or_create(
        toss_user_id="test_user_1",
        defaults={"nickname": "test"},
    )
    UserProfile.objects.get_or_create(user=user)
    return user

def get_demo_user(demo_user_num):
    """
    관리자 디버그용: demo_user 번호(1/2)로 데모 유저 반환.
    get_or_create로 없으면 자동 생성.
    """
    num = int(demo_user_num) if demo_user_num else 1
    if num not in (1, 2):
        num = 1
    toss_id = f"test_user_{num}"
    nickname = f"test{num}"
    user, _ = User.objects.get_or_create(
        toss_user_id=toss_id,
        defaults={"nickname": nickname},
    )
    UserProfile.objects.get_or_create(user=user)
    return user

def get_current_user(request):
    """
    세션 기반 유저 조회:
    1. 세션에 user_id가 있으면 해당 유저 반환
    2. demo_user 파라미터/헤더가 있으면 데모 유저 반환
    3. 없으면 로컬 개발용 test_user_1 fallback
    """
    # 1) 세션에서 user_id 확인 (토스 로그인 성공 시 저장됨)
    user_id = request.session.get("user_id") if hasattr(request, "session") else None
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            return user
        except User.DoesNotExist:
            pass  # 세션에 있지만 DB에 없으면 fallback

    # 2) Django auth 유저 (미래 확장용)
    u = getattr(request, "user", None)
    if u is not None and getattr(u, "is_authenticated", False):
        return u

    # 3) demo_user 파라미터 (개발/디버그용)
    demo = None
    if request is not None:
        demo = request.query_params.get("demo_user") or request.headers.get("X-DEMO-USER")

    if demo:
        return get_demo_user(demo)

    # 4) Fallback: 로컬 개발용 test_user
    return get_or_create_test_user()

def invalidate_recommendation_cache(user):
    """
    추천 캐시 무효화:
    추천 API는 pantry fingerprint만으로 캐시 키를 만들기 때문에,
    cook/save/skip 같은 행동 변화는 fingerprint가 안 바뀜.
    -> 액션 후 캐시 삭제를 해줘야 바로 변화가 보임.
    """
    from .models import UserPantry  # 순환 import 방지

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
        from django.core.cache import cache
        cache.delete(cache_key)

def get_user_pantry_ingredient_ids(user):
    """
    유저 냉장고 재료 ingredient_id들을 set로 반환
    (존재 여부 확인용)
    """
    return set(
        UserPantry.objects.filter(user=user)
        .values_list("ingredient_id", flat=True)
    )


def get_user_pantry_ingredient_names(user):
    """
    유저 냉장고 재료 이름들을 정규화해서 set로 반환
    (부분 매칭용)
    """
    from .models import Ingredient
    pantry_ing_ids = UserPantry.objects.filter(user=user).values_list("ingredient_id", flat=True)
    raw_names = Ingredient.objects.filter(id__in=pantry_ing_ids).values_list("name_ko", flat=True)
    # 정규화된 이름 set 반환
    return set(normalize_ingredient(name) for name in raw_names if name)


def get_user_pantry_with_expiry(user):
    """
    유저 냉장고 재료를 정규화된 이름 + 유통기한으로 반환.
    Returns:
        normalized_names: set of normalized ingredient names
        expiry_map: dict { normalized_name: expires_at (date or None) }
                    - 같은 재료가 여러 개면 가장 임박한 날짜 사용
    """
    from .models import Ingredient

    pantry_items = UserPantry.objects.filter(user=user).select_related("ingredient")

    normalized_names = set()
    expiry_map = {}  # normalized_name -> expires_at (가장 임박한 것)

    for item in pantry_items:
        raw_name = item.ingredient.name_ko
        norm_name = normalize_ingredient(raw_name)
        if not norm_name:
            continue

        normalized_names.add(norm_name)

        exp_date = item.expires_at
        if exp_date:
            # 같은 재료가 여러 개면 가장 임박한 날짜 사용
            if norm_name not in expiry_map or expiry_map[norm_name] is None:
                expiry_map[norm_name] = exp_date
            elif expiry_map[norm_name] > exp_date:
                expiry_map[norm_name] = exp_date
        else:
            # expires_at이 None인 경우, 기존 값이 없을 때만 설정
            if norm_name not in expiry_map:
                expiry_map[norm_name] = None

    return normalized_names, expiry_map


def ingredient_matches_pantry(recipe_ingredient_name, pantry_names):
    """
    레시피 재료명이 냉장고 재료와 매칭되는지 확인 (정규화 + 부분 매칭)
    예: 냉장고에 "계란"이 있으면 "달걀 2개", "전란" 등과 매칭

    Args:
        recipe_ingredient_name: 레시피 재료명 (원본)
        pantry_names: 정규화된 냉장고 재료명 set

    Returns:
        matched_name: 매칭된 pantry 재료명 (정규화된) or None
    """
    recipe_norm = normalize_ingredient(recipe_ingredient_name)
    if not recipe_norm:
        return None

    # 1. 정확히 일치
    if recipe_norm in pantry_names:
        return recipe_norm

    # 2. 부분 매칭 (pantry가 recipe에 포함되거나 그 반대)
    for pantry_name in pantry_names:
        if pantry_name in recipe_norm or recipe_norm in pantry_name:
            return pantry_name

    return None


def recommend_recipes_for_user(user, top=10):
    """
    레시피 추천 로직 (MVP v1)

    반영 요소:
    - coverage: 보유 필수 재료 비율
    - missing_ratio: 부족 재료 비율
    - expiry_bonus: 유통기한 임박 재료 포함 여부
    - time_fit: 유저 요리 가능 시간 적합도
    - diversity: 최근 행동(cook/save/skip)
    - cooldown: 최근 추천 노출 쿨타임
    """

    today = date.today()
    top_n = max(1, int(top))

    pop_cutoff = timezone.now() - timedelta(days=7)

    # recipe_id -> 유니크 유저 수
    pop_map = dict(
        RecipeAction.objects.filter(
            action__in=["cook", "save"],
            created_at__gte=pop_cutoff,
        )
        .values("recipe_id")
        .annotate(u=Count("user_id", distinct=True))
        .values_list("recipe_id", "u")
    )

    # =====================================
    # [1] 루프 전에 공통 데이터 준비
    # =====================================

    pantry_ids = get_user_pantry_ingredient_ids(user)
    # 정규화된 pantry 이름 + 유통기한 맵
    pantry_names, expiry_map = get_user_pantry_with_expiry(user)

    # 유저 프로필
    profile = getattr(user, "profile", None)
    max_time = getattr(profile, "max_cook_time_min", None) if profile else None

    # 최근 7일 행동 로그
    recent_cutoff = timezone.now() - timedelta(days=7)

    recent_cooked_saved_ids = set(
        RecipeAction.objects.filter(
            user=user,
            action__in=["save", "cook"],
            created_at__gte=recent_cutoff,
        ).values_list("recipe_id", flat=True)
    )

    recent_skipped_ids = set(
        RecipeAction.objects.filter(
            user=user,
            action="skip",
            created_at__gte=recent_cutoff,
        ).values_list("recipe_id", flat=True)
    )

    # 최근 추천 노출(쿨타임)
    recent_recommended_ids = set()
    for h in RecommendationHistory.objects.filter(user=user).order_by("-created_at")[:10]:
        for rid in (h.result_recipe_ids or []):
            recent_recommended_ids.add(rid)

    # 레시피 + 재료 프리페치
    recipes = Recipe.objects.all().prefetch_related(
        Prefetch(
            "recipe_ingredients",
            queryset=RecipeIngredient.objects.select_related("ingredient"),
        )
    )
    conv_days = 7
    conv_cutoff = timezone.now() - timedelta(days=7)

    # (A) 레시피별 추천 노출 횟수
    exposure_counts = {}
    histories = RecommendationHistory.objects.filter(
        user=user,
        created_at__gte=conv_cutoff,
    ).order_by("-created_at")[:50]

    for h in histories:
        for rid in (h.result_recipe_ids or []):
            exposure_counts[rid] = exposure_counts.get(rid, 0) + 1

    # (B) 레시피별 전환(cook/save) 발생 여부
    converted_ids = set(
        RecipeAction.objects.filter(
            user=user,
            action__in=["cook", "save"],
            created_at__gte=conv_cutoff,
        ).values_list("recipe_id", flat=True)
    )
    recipes = Recipe.objects.all().prefetch_related(
        Prefetch(
            "recipe_ingredients",
            queryset=RecipeIngredient.objects.select_related("ingredient"),
        )
    )
    
    saved_ids = set(
        UserSavedRecipe.objects.filter(user=user)
        .values_list("recipe_id", flat=True)
    )

    print("DEBUG_COUNTS:",
      "cooked_saved=", len(recent_cooked_saved_ids),
      "skipped=", len(recent_skipped_ids),
      "converted=", len(converted_ids),
      "recent_reco=", len(recent_recommended_ids),
      "histories=", histories.count())

    # =====================================
    # [2] 레시피 루프
    # =====================================

    results = []

    for r in recipes:

        if r.id in saved_ids:
            continue  # 저장된 레시피는 추천에서 제외
        
        # 필수 재료만
        required_items = [
            ri for ri in r.recipe_ingredients.all()
            if not ri.is_optional
        ]
        required_count = len(required_items)

        if required_count == 0:
            continue

        # 부분 매칭: ID 매칭 또는 정규화 이름 매칭 + 유통기한 추적
        have_count = 0
        missing_items = []
        matched_expiry_info = []  # 매칭된 재료 중 유통기한 있는 것들

        for ri in required_items:
            ing_name = ri.ingredient.name_ko
            matched_pantry_name = ingredient_matches_pantry(ing_name, pantry_names)

            if ri.ingredient_id in pantry_ids or matched_pantry_name:
                have_count += 1
                # 유통기한 정보 추적 (매칭된 pantry 재료 기준)
                if matched_pantry_name and matched_pantry_name in expiry_map:
                    exp_date = expiry_map[matched_pantry_name]
                    if exp_date:
                        days_left = (exp_date - today).days
                        matched_expiry_info.append({
                            "name": ing_name,
                            "pantry_name": matched_pantry_name,
                            "expires_at": exp_date,
                            "days_left": days_left,
                        })
            else:
                missing_items.append(ri)

        missing_count = required_count - have_count
        coverage = have_count / required_count
        missing_ratio = missing_count / required_count

        # =============================================
        # 유통기한 기반 보너스/패널티 계산 (세분화)
        # =============================================
        bonus_expiry = 0.0
        penalty_expired = 0.0
        expiry_min_days = None

        for info in matched_expiry_info:
            days_left = info["days_left"]

            # 가장 임박한 날짜 추적
            if expiry_min_days is None or days_left < expiry_min_days:
                expiry_min_days = days_left

            if days_left <= -1:
                # 이미 지남 (expired)
                penalty_expired += 0.20
            elif days_left <= 2:
                # 0~2일 남음: 긴급
                bonus_expiry += 0.25
            elif days_left <= 7:
                # 3~7일 남음: 임박
                bonus_expiry += 0.10
            # 8일 이상: 보너스 없음

        # cap 적용 (최대 보너스 +0.5, 최대 패널티 -0.5)
        bonus_expiry = min(bonus_expiry, 0.5)
        penalty_expired = min(penalty_expired, 0.5)

        # 시간 적합도
        cook_time = getattr(r, "cook_time_min", None)
        if max_time and cook_time is not None and max_time > 0:
            diff = abs(cook_time - max_time) / max_time
            time_fit = max(0.0, 1.0 - min(diff, 1.0))
        else:
            time_fit = 0.5

        # 기본 점수 (유통기한 보너스/패널티 반영)
        score = (
            0.55 * coverage
            - 0.20 * missing_ratio
            + bonus_expiry           # 유통기한 임박 보너스
            - penalty_expired        # 유통기한 만료 패널티
            + 0.10 * time_fit
        )

        # 다양성 / 피드백 (중복 제거됨)
        if r.id in recent_cooked_saved_ids:
            score -= 0.15
        if r.id in recent_skipped_ids:
            score -= 0.40
        if r.id in recent_recommended_ids:
            score -= 0.10

        # 전환율 피드백 감점/보너스 (루프 안에!)
        exp = exposure_counts.get(r.id, 0)
        is_converted = (r.id in converted_ids)

        if exp >= 2 and not is_converted:
            score -= 0.20

        if is_converted:
            score += 0.05

        # 부족 재료 이름 (이미 위에서 missing_items 계산됨)
        missing_names = [ri.ingredient.name_ko for ri in missing_items]

        pop_users = pop_map.get(r.id, 0)
        # 너무 세게 먹이면 개인화가 죽음 → 상한을 둔다
        # 예: 유저 20명 이상이면 더 올라가지 않게 캡
        pop_norm = min(pop_users, 20) / 20.0  # 0~1
        # 가산점은 작게(서비스스럽게)
        score += 0.08 * pop_norm

        debug = {
            "base": round(
                0.55 * coverage
                - 0.20 * missing_ratio
                + 0.10 * time_fit,
                4
            ),
            "penalty_recent_cooked_saved": (-0.15 if r.id in recent_cooked_saved_ids else 0.0),
            "penalty_recent_skipped": (-0.40 if r.id in recent_skipped_ids else 0.0),
            "penalty_cooldown": (-0.10 if r.id in recent_recommended_ids else 0.0),
            "penalty_exposure_no_convert": (
                -0.20 if exposure_counts.get(r.id, 0) >= 2 and r.id not in converted_ids else 0.0
            ),
            "bonus_converted": (0.05 if r.id in converted_ids else 0.0),
            "exposure": exposure_counts.get(r.id, 0),
            "converted": (r.id in converted_ids),
            "pop_users": pop_users,
            "pop_bonus": round(0.08 * pop_norm, 4),
            # 유통기한 관련 debug 정보
            "bonus_expiry": round(bonus_expiry, 4),
            "penalty_expired_pantry": round(penalty_expired, 4),
            "expiry_matched_count": len(matched_expiry_info),
            "expiry_min_days_left": expiry_min_days,
        }

        # 추천 이유
        reasons = []
        if missing_count == 0:
            reasons.append("냉장고 재료로 바로 가능")
        else:
            reasons.append(f"필수 재료 {have_count}/{required_count}개 보유")
        if bonus_expiry > 0:
            reasons.append("유통기한 임박 재료 활용")
        if penalty_expired > 0:
            reasons.append("유통기한 지난 재료 포함")
        if cook_time is not None:
            reasons.append(f"{cook_time}분 내 조리")


        results.append(
            {
                "recipe_id": r.id,
                "title": getattr(r, "title", ""),
                "cook_time_min": cook_time,
                "coverage": round(coverage, 3),
                "missing_count": missing_count,
                "missing_ingredients": missing_names,
                "shopping_list": missing_names,
                "reasons": reasons,
                "saved": (r.id in saved_ids),
                "score": round(score, 4),
                "debug": debug,
            }
        )

    # =====================================
    # [3] 정렬 + fallback
    # =====================================

    results.sort(key=lambda x: x["score"], reverse=True)
    picked = results[:top_n]

    if not picked:
        fallback = [x for x in results if 0 < x["missing_count"] <= 2]
        picked = fallback[:top_n] if fallback else []

    if not picked:
        return [
            {
                "recipe_id": 0,
                "title": "추천할 레시피가 아직 부족해요",
                "cook_time_min": None,
                "coverage": 0.0,
                "missing_count": 0,
                "missing_ingredients": [],
                "shopping_list": [],
                "reasons": ["레시피 데이터를 더 추가하면 추천이 가능해요"],
                "score": 0.0,
            }
        ]

    return picked


def score_single_recipe_for_user(user, recipe_id, exclude_saved=False):
    """
    특정 recipe_id 하나에 대해 유저 기준 추천 점수/디버그를 계산.
    recommend_recipes_for_user와 동일 로직이나 단일 레시피만 평가.
    exclude_saved=False면 저장된 레시피도 계산 결과를 반환.
    """
    today = date.today()

    try:
        r = Recipe.objects.prefetch_related(
            Prefetch(
                "recipe_ingredients",
                queryset=RecipeIngredient.objects.select_related("ingredient"),
            )
        ).get(id=recipe_id)
    except Recipe.DoesNotExist:
        return None

    saved_ids = set(
        UserSavedRecipe.objects.filter(user=user)
        .values_list("recipe_id", flat=True)
    )

    if exclude_saved and r.id in saved_ids:
        return None

    pantry_ids = get_user_pantry_ingredient_ids(user)
    # 정규화된 pantry 이름 + 유통기한 맵
    pantry_names, expiry_map = get_user_pantry_with_expiry(user)

    profile = getattr(user, "profile", None)
    max_time = getattr(profile, "max_cook_time_min", None) if profile else None

    recent_cutoff = timezone.now() - timedelta(days=7)

    recent_cooked_saved_ids = set(
        RecipeAction.objects.filter(
            user=user,
            action__in=["save", "cook"],
            created_at__gte=recent_cutoff,
        ).values_list("recipe_id", flat=True)
    )

    recent_skipped_ids = set(
        RecipeAction.objects.filter(
            user=user,
            action="skip",
            created_at__gte=recent_cutoff,
        ).values_list("recipe_id", flat=True)
    )

    recent_recommended_ids = set()
    for h in RecommendationHistory.objects.filter(user=user).order_by("-created_at")[:10]:
        for rid in (h.result_recipe_ids or []):
            recent_recommended_ids.add(rid)

    conv_cutoff = timezone.now() - timedelta(days=7)
    exposure_counts = {}
    histories = RecommendationHistory.objects.filter(
        user=user,
        created_at__gte=conv_cutoff,
    ).order_by("-created_at")[:50]
    for h in histories:
        for rid in (h.result_recipe_ids or []):
            exposure_counts[rid] = exposure_counts.get(rid, 0) + 1

    converted_ids = set(
        RecipeAction.objects.filter(
            user=user,
            action__in=["cook", "save"],
            created_at__gte=conv_cutoff,
        ).values_list("recipe_id", flat=True)
    )

    pop_cutoff = timezone.now() - timedelta(days=7)
    pop_map = dict(
        RecipeAction.objects.filter(
            action__in=["cook", "save"],
            created_at__gte=pop_cutoff,
        )
        .values("recipe_id")
        .annotate(u=Count("user_id", distinct=True))
        .values_list("recipe_id", "u")
    )

    # 필수 재료 계산
    required_items = [
        ri for ri in r.recipe_ingredients.all()
        if not ri.is_optional
    ]
    required_count = len(required_items)

    if required_count == 0:
        return {
            "recipe_id": r.id,
            "title": r.title,
            "cook_time_min": r.cook_time_min,
            "coverage": 0.0,
            "missing_count": 0,
            "missing_ingredients": [],
            "shopping_list": [],
            "reasons": ["필수 재료 정보 없음"],
            "saved": (r.id in saved_ids),
            "score": 0.0,
            "debug": {},
        }

    # 부분 매칭: ID 매칭 또는 정규화 이름 매칭 + 유통기한 추적
    have_count = 0
    missing_items = []
    matched_expiry_info = []

    for ri in required_items:
        ing_name = ri.ingredient.name_ko
        matched_pantry_name = ingredient_matches_pantry(ing_name, pantry_names)

        if ri.ingredient_id in pantry_ids or matched_pantry_name:
            have_count += 1
            # 유통기한 정보 추적
            if matched_pantry_name and matched_pantry_name in expiry_map:
                exp_date = expiry_map[matched_pantry_name]
                if exp_date:
                    days_left = (exp_date - today).days
                    matched_expiry_info.append({
                        "name": ing_name,
                        "pantry_name": matched_pantry_name,
                        "expires_at": exp_date,
                        "days_left": days_left,
                    })
        else:
            missing_items.append(ri)

    missing_count = required_count - have_count
    coverage = have_count / required_count
    missing_ratio = missing_count / required_count

    # 유통기한 기반 보너스/패널티 계산
    bonus_expiry = 0.0
    penalty_expired = 0.0
    expiry_min_days = None

    for info in matched_expiry_info:
        days_left = info["days_left"]
        if expiry_min_days is None or days_left < expiry_min_days:
            expiry_min_days = days_left

        if days_left <= -1:
            penalty_expired += 0.20
        elif days_left <= 2:
            bonus_expiry += 0.25
        elif days_left <= 7:
            bonus_expiry += 0.10

    bonus_expiry = min(bonus_expiry, 0.5)
    penalty_expired = min(penalty_expired, 0.5)

    cook_time = r.cook_time_min
    if max_time and cook_time is not None and max_time > 0:
        diff = abs(cook_time - max_time) / max_time
        time_fit = max(0.0, 1.0 - min(diff, 1.0))
    else:
        time_fit = 0.5

    score = (
        0.55 * coverage
        - 0.20 * missing_ratio
        + bonus_expiry
        - penalty_expired
        + 0.10 * time_fit
    )

    if r.id in recent_cooked_saved_ids:
        score -= 0.15
    if r.id in recent_skipped_ids:
        score -= 0.40
    if r.id in recent_recommended_ids:
        score -= 0.10

    exp = exposure_counts.get(r.id, 0)
    is_converted = (r.id in converted_ids)
    if exp >= 2 and not is_converted:
        score -= 0.20
    if is_converted:
        score += 0.05

    pop_users = pop_map.get(r.id, 0)
    pop_norm = min(pop_users, 20) / 20.0
    score += 0.08 * pop_norm

    missing_names = [ri.ingredient.name_ko for ri in missing_items]

    debug = {
        "base": round(
            0.55 * coverage
            - 0.20 * missing_ratio
            + 0.10 * time_fit,
            4
        ),
        "penalty_recent_cooked_saved": (-0.15 if r.id in recent_cooked_saved_ids else 0.0),
        "penalty_recent_skipped": (-0.40 if r.id in recent_skipped_ids else 0.0),
        "penalty_cooldown": (-0.10 if r.id in recent_recommended_ids else 0.0),
        "penalty_exposure_no_convert": (
            -0.20 if exp >= 2 and not is_converted else 0.0
        ),
        "bonus_converted": (0.05 if is_converted else 0.0),
        "exposure": exp,
        "converted": is_converted,
        "pop_users": pop_users,
        "pop_bonus": round(0.08 * pop_norm, 4),
        # 유통기한 관련 debug 정보
        "bonus_expiry": round(bonus_expiry, 4),
        "penalty_expired_pantry": round(penalty_expired, 4),
        "expiry_matched_count": len(matched_expiry_info),
        "expiry_min_days_left": expiry_min_days,
    }

    reasons = []
    if missing_count == 0:
        reasons.append("냉장고 재료로 바로 가능")
    else:
        reasons.append(f"필수 재료 {have_count}/{required_count}개 보유")
    if bonus_expiry > 0:
        reasons.append("유통기한 임박 재료 활용")
    if penalty_expired > 0:
        reasons.append("유통기한 지난 재료 포함")
    if cook_time is not None:
        reasons.append(f"{cook_time}분 내 조리")

    return {
        "recipe_id": r.id,
        "title": r.title,
        "cook_time_min": cook_time,
        "coverage": round(coverage, 3),
        "missing_count": missing_count,
        "missing_ingredients": missing_names,
        "shopping_list": missing_names,
        "reasons": reasons,
        "saved": (r.id in saved_ids),
        "score": round(score, 4),
        "debug": debug,
    }


# =============================================
# 토스 인앱 로그인 관련 함수
# =============================================
import requests
from django.conf import settings


def toss_generate_token(authorization_code: str, referrer: str) -> dict:
    """
    토스 앱인토스 OAuth2 토큰 발급
    POST /api-partner/v1/apps-in-toss/user/oauth2/generate-token

    Returns: { "accessToken": "...", "refreshToken": "...", "expiresIn": 3600 }
    Raises: Exception on API error
    """
    url = f"{settings.TOSS_API_BASE_URL}/api-partner/v1/apps-in-toss/user/oauth2/generate-token"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.TOSS_PARTNER_KEY}",
    }
    payload = {
        "authorizationCode": authorization_code,
        "referrer": referrer,
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=10)

    if resp.status_code != 200:
        raise Exception(f"Toss generate-token failed: {resp.status_code} {resp.text}")

    return resp.json()


def toss_get_user_info(access_token: str) -> dict:
    """
    토스 앱인토스 유저 정보 조회
    GET /api-partner/v1/apps-in-toss/user/oauth2/login-me

    Returns: { "userKey": "...", ... }
    Raises: Exception on API error
    """
    url = f"{settings.TOSS_API_BASE_URL}/api-partner/v1/apps-in-toss/user/oauth2/login-me"
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    resp = requests.get(url, headers=headers, timeout=10)

    if resp.status_code != 200:
        raise Exception(f"Toss login-me failed: {resp.status_code} {resp.text}")

    return resp.json()


def get_or_create_user_by_toss_id(toss_user_id: str) -> User:
    """
    토스 userKey로 우리 DB User 조회/생성
    """
    user, created = User.objects.get_or_create(
        toss_user_id=str(toss_user_id),
        defaults={"nickname": f"toss_{toss_user_id[:8]}"},
    )
    UserProfile.objects.get_or_create(user=user)
    return user

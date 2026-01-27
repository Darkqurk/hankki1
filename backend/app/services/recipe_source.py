from datetime import timedelta
from django.utils import timezone
from app.models import ExternalRecipeCache
from app.external.foodsafety import fetch_recipes_json
import requests
from django.conf import settings

CACHE_TTL_MIN = 60  # 1시간 캐시 (MVP 적당)

def get_foodsafety_recipes(start=1, end=50, name_query=None):
    cache_key = f"recipes:name={name_query or ''}:start={start}:end={end}"

    obj = ExternalRecipeCache.objects.filter(
        provider="foodsafety", cache_key=cache_key
    ).first()

    if obj:
        age = timezone.now() - obj.fetched_at
        if age < timedelta(minutes=CACHE_TTL_MIN):
            return obj.payload  # 캐시 HIT

    payload = fetch_recipes_json(start=start, end=end, name_query=name_query)

    ExternalRecipeCache.objects.update_or_create(
        provider="foodsafety",
        cache_key=cache_key,
        defaults={"payload": payload},
    )
    return payload

BASE_URL = "https://openapi.foodsafetykorea.go.kr/api"

def get_foodsafety_recipes(start=1, end=20, name_query=None):
    """
    식약처 레시피 API(COOKRCP01) 호출
    """
    key = settings.FOODS_API_KEY
    if not key:
        raise RuntimeError("FOODS_API_KEY is empty")

    url = f"{BASE_URL}/{key}/COOKRCP01/json/{start}/{end}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    print("FOODSAFETY status:", resp.status_code)
    print("FOODSAFETY url:", resp.url)
    print("FOODSAFETY keys:", list(data.keys()) if isinstance(data, dict) else type(data))
    print("FOODSAFETY COOKRCP01:", data.get("COOKRCP01", {}).get("total_count"), data.get("COOKRCP01", {}).get("RESULT"))


    # name_query 있으면 간단 필터링(MVP)
    if name_query:
        rows = data.get("COOKRCP01", {}).get("row", []) or []
        q = name_query.strip()
        rows = [r for r in rows if q in (r.get("RCP_NM") or "")]
        data["COOKRCP01"]["row"] = rows

    return data
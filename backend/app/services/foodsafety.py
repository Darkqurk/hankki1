import requests
from django.conf import settings

BASE_URL = "https://openapi.foodsafetykorea.go.kr/api"


def get_foodsafety_recipes(start=1, end=20, name_query=None):
    key = getattr(settings, "FOODS_API_KEY", "") or ""
    if not key:
        raise RuntimeError("FOODS_API_KEY is empty")

    url = f"{BASE_URL}/{key}/COOKRCP01/json/{start}/{end}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # name_query 있으면 간단 필터링(MVP)
    if name_query:
        rows = data.get("COOKRCP01", {}).get("row", []) or []
        q = name_query.strip()
        rows = [r for r in rows if q in (r.get("RCP_NM") or "")]
        data["COOKRCP01"]["row"] = rows

    return data

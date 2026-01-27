import requests
from django.conf import settings

BASE = "http://openapi.foodsafetykorea.go.kr/api"

def fetch_recipes_json(start=1, end=50, name_query=None):
    """
    COOKRCP01 레시피 목록 조회
    - dataType: json
    - startIdx/endIdx: 범위
    - RCP_NM: 메뉴명 검색(선택)
    """
    key = settings.FOODS_API_KEY
    if not key:
        raise RuntimeError("FOODS_API_KEY가 비어있음")

    url = f"{BASE}/{key}/COOKRCP01/json/{start}/{end}"
    if name_query:
        # 공식 문서에 RCP_NM 추가 파라미터 존재 :contentReference[oaicite:4]{index=4}
        url += f"/RCP_NM={name_query}"

    res = requests.get(url, timeout=10)
    res.raise_for_status()
    return res.json()

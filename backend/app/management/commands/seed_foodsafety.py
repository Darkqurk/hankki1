from django.core.management.base import BaseCommand
from app.services.recipe_source import get_foodsafety_recipes
from app.services.seed_foodsafety import seed_from_foodsafety_rows
from app.models import Recipe, AppSetting


class Command(BaseCommand):
    help = "Seed recipes from foodsafety API into DB (upsert: 빈 이미지 필드만 채움)"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=30)
        parser.add_argument("--query", type=str, default="")
        parser.add_argument("--start", type=int, default=None)
        parser.add_argument(
            "--force-update",
            action="store_true",
            help="기존 레코드도 이미지 보강 시도 (기본: 새 레코드만 생성)"
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        query = options["query"].strip() or None
        force_update = options["force_update"]

        PAGE_SIZE = 200  # API 한번 호출 범위

        # 마지막 위치 불러오기 (없으면 1부터)
        setting, _ = AppSetting.objects.get_or_create(
            key="foodsafety_last_start",
            defaults={"value": "1"}
        )

        # --start 옵션이 명시되면 그 값 사용, 아니면 저장된 위치
        if options["start"] is not None:
            start = options["start"]
        else:
            start = int(setting.value or "1")

        end = start + PAGE_SIZE - 1

        payload = get_foodsafety_recipes(
            start=start,
            end=end,
            name_query=None,
        )

        # 다음 실행 때 start를 밀어두기
        next_start = end + 1
        TOTAL = 1146  # MVP 하드코딩
        if next_start > TOTAL:
            next_start = 1

        setting.value = str(next_start)
        setting.save()
        self.stdout.write(f"ROTATE: start={start}, end={end}, next_start={next_start}")

        # rows 추출
        rows = payload.get("COOKRCP01", {}).get("row", []) or []

        # query 필터
        if query:
            q = query.strip()
            rows = [r for r in rows if q in (r.get("RCP_NM") or "")]

        # ✅ force_update=False일 때만 기존 레코드 스킵
        # force_update=True면 기존 레코드도 이미지 보강 시도
        if not force_update:
            row_external_ids = []
            for r in rows:
                external_id = (r.get("RCP_SEQ") or "").strip()
                if external_id:
                    row_external_ids.append(external_id)

            existing_ids = set(
                Recipe.objects.filter(
                    external_source="foodsafety",
                    external_id__in=row_external_ids,
                ).values_list("external_id", flat=True)
            )

            before = len(rows)
            rows = [
                r for r in rows
                if (r.get("RCP_SEQ") or "").strip() not in existing_ids
            ]
            after = len(rows)
            self.stdout.write(f"DEDUP: before={before}, after={after}, skipped={before-after}")
        else:
            self.stdout.write(f"FORCE_UPDATE: 기존 레코드도 이미지 보강 시도 (rows={len(rows)})")

        rows = rows[:limit]

        if rows:
            self.stdout.write(f"ROWS COUNT = {len(rows)}")
            self.stdout.write(f"FIRST TITLE = {rows[0].get('RCP_NM')}")
        else:
            self.stdout.write("No rows to process")

        result = seed_from_foodsafety_rows(rows, limit=limit)
        self.stdout.write(self.style.SUCCESS(f"OK seed: {result}"))

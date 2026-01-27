from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db import transaction
from app.models import Recipe, RecipeIngredient, RecipeStep


def _unique_merge_lists(existing: list, new_items: list) -> list:
    """두 리스트를 병합하고 중복/빈 값 제거."""
    existing = existing or []
    new_items = new_items or []
    result = []
    seen = set()
    for item in existing:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    for item in new_items:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _calc_image_score(recipe):
    """
    이미지 풍부도 점수 계산.
    - image_url 있음: +1
    - image_url_small 있음: +1
    - instruction_images 길이: +len
    - steps 중 image_url 있는 개수: +count
    """
    score = 0
    if recipe.image_url:
        score += 1
    if recipe.image_url_small:
        score += 1
    if recipe.instruction_images:
        score += len(recipe.instruction_images)
    # RecipeStep 이미지 개수
    step_img_count = recipe.steps.exclude(image_url="").count()
    score += step_img_count
    return score


class Command(BaseCommand):
    help = "Deduplicate foodsafety recipes: merge images into winner, delete losers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print only, no delete/update"
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed merge info"
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        verbose = options["verbose"]

        # foodsafety 레시피 중 external_id가 있는 것만
        # 대소문자 구분 없이 검색
        qs = Recipe.objects.filter(
            external_source__iexact="foodsafety"
        ).exclude(external_id="")

        # 중복 그룹 찾기
        dup_keys = (
            qs.values("external_id")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
        )

        total_groups = dup_keys.count()
        self.stdout.write(self.style.WARNING(f"Found {total_groups} duplicate groups"))

        merged_count = 0
        deleted_count = 0

        for key in dup_keys:
            ext_id = key["external_id"]

            group = list(
                Recipe.objects.filter(
                    external_source__iexact="foodsafety",
                    external_id=ext_id,
                ).order_by("-id")
            )

            if len(group) < 2:
                continue

            # 점수 기반 winner 선택 (점수 높은 것, 동점이면 id 낮은 것)
            scored = [(r, _calc_image_score(r)) for r in group]
            scored.sort(key=lambda x: (-x[1], x[0].id))  # 점수 내림차순, id 오름차순
            winner, winner_score = scored[0]
            losers = [r for r, s in scored[1:]]

            if verbose:
                self.stdout.write(f"\n[GROUP] external_id={ext_id}")
                for r, s in scored:
                    self.stdout.write(f"  - id={r.id} score={s} img={bool(r.image_url)}")
                self.stdout.write(f"  WINNER: id={winner.id}")

            # ========================================
            # 이미지 병합: losers -> winner (빈 필드만 채움)
            # ========================================
            fields_to_update = []

            for loser in losers:
                # image_url
                if not winner.image_url and loser.image_url:
                    winner.image_url = loser.image_url
                    if "image_url" not in fields_to_update:
                        fields_to_update.append("image_url")
                    if verbose:
                        self.stdout.write(f"  [MERGE] image_url from {loser.id}")

                # image_url_small
                if not winner.image_url_small and loser.image_url_small:
                    winner.image_url_small = loser.image_url_small
                    if "image_url_small" not in fields_to_update:
                        fields_to_update.append("image_url_small")
                    if verbose:
                        self.stdout.write(f"  [MERGE] image_url_small from {loser.id}")

                # instruction_images (리스트 병합)
                if loser.instruction_images:
                    merged = _unique_merge_lists(
                        winner.instruction_images,
                        loser.instruction_images
                    )
                    if merged != winner.instruction_images:
                        winner.instruction_images = merged
                        if "instruction_images" not in fields_to_update:
                            fields_to_update.append("instruction_images")
                        if verbose:
                            self.stdout.write(f"  [MERGE] instruction_images from {loser.id}")

                # raw_ingredients
                if not winner.raw_ingredients and loser.raw_ingredients:
                    winner.raw_ingredients = loser.raw_ingredients
                    if "raw_ingredients" not in fields_to_update:
                        fields_to_update.append("raw_ingredients")

            # winner 저장
            if fields_to_update and not dry_run:
                winner.save(update_fields=fields_to_update)
                merged_count += 1

            # ========================================
            # losers 삭제 (FK cascade로 ingredients/steps도 삭제됨)
            # ========================================
            for loser in losers:
                self.stdout.write(
                    f"[DELETE] id={loser.id} ext_id={loser.external_id} "
                    f"img={'Y' if loser.image_url else 'N'} "
                    f"title={loser.title[:30]}"
                )
                if not dry_run:
                    # RecipeIngredient, RecipeStep은 CASCADE로 자동 삭제
                    loser.delete()
                    deleted_count += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done. merged={merged_count}, deleted={deleted_count}"
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING("(DRY RUN - no actual changes)"))

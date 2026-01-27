import re
from app.models import Recipe, Ingredient, RecipeIngredient, RecipeStep


def _split_ingredients(text: str):
    """
    MVP용: 재료 텍스트를 대충 잘라서 ingredient 이름 목록 만들기.
    (정교한 파싱은 나중에)
    """
    if not text:
        return []
    # 줄바꿈/쉼표 기준으로 분리
    parts = re.split(r"[\n,]", text)
    cleaned = []
    for p in parts:
        name = p.strip()
        if not name:
            continue
        cleaned.append(name)
    return cleaned


def _unique_merge_lists(existing: list, new_items: list) -> list:
    """
    두 리스트를 병합하고 중복/빈 값 제거.
    순서 유지: existing 먼저, 그 다음 new_items 중 없는 것만 추가.
    """
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


def seed_from_foodsafety_rows(rows, limit=20):
    """
    rows: COOKRCP01 row 리스트
    limit: 최대 저장 개수
    return: {"created": X, "updated": Y, "skipped": Z}

    Upsert 로직:
    - external_id(RCP_SEQ)로 기존 레시피 조회
    - 있으면: 빈 필드만 채움 (기존 값 보존)
    - 없으면: 새로 생성
    """
    created, updated, skipped = 0, 0, 0

    for row in rows[:limit]:
        title = (row.get("RCP_NM") or "").strip()
        if not title:
            skipped += 1
            continue

        # ✅ external_id는 RCP_SEQ 필수 - 없으면 스킵
        raw_seq = (row.get("RCP_SEQ") or "").strip()
        if not raw_seq:
            print(f"[SKIP] RCP_SEQ 없음: {title}")
            skipped += 1
            continue

        external_id = raw_seq

        # 대표 이미지(대/소)
        img_large = (row.get("ATT_FILE_NO_MAIN") or "").strip()
        img_small = (row.get("ATT_FILE_NO_MK") or "").strip()

        # 재료 원문
        parts_text = row.get("RCP_PARTS_DTLS") or ""

        # 조리 단계 이미지 리스트 추출
        step_images = []
        for i in range(1, 21):
            key_img = f"MANUAL_IMG{str(i).zfill(2)}"
            img = (row.get(key_img) or "").strip()
            if img:
                step_images.append(img)

        # ✅ 기존 레시피 조회
        existing_recipe = Recipe.objects.filter(
            external_source="foodsafety",
            external_id=external_id,
        ).first()

        if existing_recipe:
            # ========================================
            # UPDATE: 빈 필드만 채움 (기존 값 보존)
            # ========================================
            recipe = existing_recipe
            fields_to_update = []

            # image_url: 비어있을 때만 채움
            if not recipe.image_url and (img_large or img_small):
                recipe.image_url = img_large or img_small
                fields_to_update.append("image_url")

            # image_url_small: 비어있을 때만 채움
            if not recipe.image_url_small and img_small:
                recipe.image_url_small = img_small
                fields_to_update.append("image_url_small")

            # instruction_images: 리스트 병합 (중복 제거)
            if step_images:
                merged_imgs = _unique_merge_lists(recipe.instruction_images, step_images)
                if merged_imgs != recipe.instruction_images:
                    recipe.instruction_images = merged_imgs
                    fields_to_update.append("instruction_images")

            # raw_ingredients: 비어있을 때만 채움
            if not recipe.raw_ingredients and parts_text:
                recipe.raw_ingredients = parts_text
                fields_to_update.append("raw_ingredients")

            # title은 항상 있으므로 건드리지 않음

            if fields_to_update:
                recipe.save(update_fields=fields_to_update)
                print(f"[UPDATE] {recipe.id}: {title} - fields: {fields_to_update}")
                updated += 1
            else:
                # 업데이트할 필드가 없으면 스킵 카운트
                skipped += 1
                continue

        else:
            # ========================================
            # CREATE: 새 레시피 생성
            # ========================================
            cook_time_raw = row.get("RCP_COOK_TIME") or ""
            try:
                cook_time_min = int(cook_time_raw) if cook_time_raw.strip() else None
            except (ValueError, TypeError):
                cook_time_min = None

            recipe = Recipe.objects.create(
                external_source="foodsafety",
                external_id=external_id,
                title=title,
                cook_time_min=cook_time_min,
                source="MFDS",
                source_recipe_id=raw_seq,
                image_url=img_large or img_small,
                image_url_small=img_small,
                raw_ingredients=parts_text,
                instruction_images=step_images,
            )
            print(f"[CREATE] {recipe.id}: {title}")
            created += 1

        # ========================================
        # 재료/스텝 처리 (새로 생성된 경우에만)
        # 기존 레시피는 재료/스텝을 덮어쓰지 않음
        # ========================================
        if not existing_recipe:
            # 1) 재료 저장
            ing_names = _split_ingredients(parts_text)
            for name in ing_names:
                ing, _ = Ingredient.objects.get_or_create(name_ko=name)
                RecipeIngredient.objects.update_or_create(
                    recipe=recipe,
                    ingredient=ing,
                    defaults={
                        "amount_text": "",
                        "is_optional": False,
                    },
                )

            # 2) 조리 단계 저장
            step_no = 1
            for i in range(1, 21):
                key_txt = f"MANUAL{str(i).zfill(2)}"
                key_img = f"MANUAL_IMG{str(i).zfill(2)}"

                txt = (row.get(key_txt) or "").strip()
                img = (row.get(key_img) or "").strip()

                if not txt:
                    continue

                RecipeStep.objects.create(
                    recipe=recipe,
                    step_no=step_no,
                    description=txt,
                    image_url=img,
                )
                step_no += 1

    return {"created": created, "updated": updated, "skipped": skipped}

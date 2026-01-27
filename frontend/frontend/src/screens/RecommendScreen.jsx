import { Link } from "react-router-dom";
import { getRecommendations, saveRecipe, recipeAction, searchRecipes } from "../api";
import { useEffect, useState, useMemo, useCallback } from "react";

// Debounce function
const debounce = (func, delay) => {
    let timeoutId;
    return (...args) => {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
        timeoutId = setTimeout(() => {
            func(...args);
        }, delay);
    };
};

const ACTION_LABELS = {
    cook: "요리함",
    save: "저장",
    skip: "스킵",
};

export default function RecommendScreen({ pantryRev }) {
    const [top, setTop] = useState(5);
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);

    // 검색 관련 상태
    const [query, setQuery] = useState("");
    const [isSearchMode, setIsSearchMode] = useState(false);

    // 피드백 배너 상태
    const [feedback, setFeedback] = useState(null); // { action, title, before, after, hidden }

    const showFeedback = (action, title, { before = null, after = null, hidden = false } = {}) => {
        setFeedback({ action, title, before, after, hidden });
        setTimeout(() => setFeedback(null), 3500);
    };

    const load = async () => {
        setLoading(true);
        try {
            const data = await getRecommendations(top);
            setItems(data);
            setIsSearchMode(false);
            return data;
        } finally {
            setLoading(false);
        }
    };

    // 검색 실행
    const handleSearch = async () => {
        const q = query.trim();
        if (!q) {
            load(); // 검색어 비면 추천으로 복귀
            return;
        }

        setLoading(true);
        try {
            const data = await searchRecipes(q);
            setItems(data);
            setIsSearchMode(true);
        } finally {
            setLoading(false);
        }
    };

    // Enter 키 처리
    const handleKeyDown = (e) => {
        if (e.key === "Enter") {
            handleSearch();
        }
    };

    // 초기화 (추천으로 복귀)
    const handleReset = () => {
        setQuery("");
        load();
    };

    useEffect(() => {
        load();
    }, [top, pantryRev]);

    const handleSave = async (e, recipeId, recipeTitle) => {
        e.preventDefault();
        e.stopPropagation();
        await saveRecipe(recipeId);
        showFeedback("save", recipeTitle, { hidden: true });
        await load();
    };

    const handleAction = useCallback(async (recipeId, action, recipeTitle) => {
        // 액션 전 점수 기록
        const beforeItem = items.find((r) => r.recipe_id === recipeId);
        const beforeScore = beforeItem?.score ?? null;

        await recipeAction(recipeId, action);
        const newData = await load();

        // 액션 후 점수 비교
        const afterItem = (newData || []).find((r) => r.recipe_id === recipeId);
        if (!afterItem) {
            // 리스트에서 빠짐 (스킵 등)
            showFeedback(action, recipeTitle, { before: beforeScore, after: null, hidden: true });
        } else {
            showFeedback(action, recipeTitle, { before: beforeScore, after: afterItem.score });
        }
    }, [items, top, query]);

    const debouncedAction = useMemo(
        () => debounce(handleAction, 300),
        [handleAction]
    );

    // coverage 안전 표시
    const formatCoverage = (coverage) => {
        if (coverage === undefined || coverage === null) return null;
        const val = coverage <= 1 ? (coverage * 100).toFixed(0) : Number(coverage).toFixed(0);
        return `${val}%`;
    };

    return (
        <div className="page">
            {/* 헤더 */}
            <div className="card header-card">
                <h2 className="title">냉장고 한끼</h2>
                <p className="sub">냉장고 재료 기반 맞춤 레시피 추천</p>

                <div className="row mt12">
                    <label className="label">추천 개수</label>
                    <select
                        value={top}
                        onChange={(e) => setTop(Number(e.target.value))}
                        className="select"
                    >
                        <option value={3}>3개</option>
                        <option value={5}>5개</option>
                        <option value={10}>10개</option>
                    </select>

                    <button className="btn ghost" onClick={load}>
                        새로고침
                    </button>
                </div>

                {/* 검색 UI */}
                <div className="row mt12" style={{ gap: "8px" }}>
                    <input
                        className="input"
                        style={{ flex: 1 }}
                        placeholder="레시피 제목 검색..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={handleKeyDown}
                    />
                    <button className="btn primary" onClick={handleSearch}>
                        검색
                    </button>
                    {isSearchMode && (
                        <button className="btn ghost" onClick={handleReset}>
                            초기화
                        </button>
                    )}
                </div>
                {isSearchMode && (
                    <p className="tiny muted mt8">
                        "{query}" 검색 결과 ({items.length}건)
                    </p>
                )}
            </div>

            {/* 피드백 배너 */}
            {feedback && (
            <div className="feedback-banner mt8">
                <span className="feedback-icon">✓</span>
                <span>
                <strong>{ACTION_LABELS[feedback.action] || feedback.action}</strong> 반영 완료
                {feedback.title && <> — <em>{feedback.title}</em></>}

                {feedback.hidden ? (
                    <div className="tiny muted mt4">숨김 처리됨 (추천에서 제외)</div>
                ) : feedback.before !== null && feedback.after !== null ? (
                    <div className="tiny muted mt4">
                        점수 변화: {feedback.before.toFixed(2)} → {feedback.after.toFixed(2)}{" "}
                        (Δ {(feedback.after - feedback.before) >= 0 ? "+" : ""}{(feedback.after - feedback.before).toFixed(2)})
                    </div>
                ) : null}
                </span>
            </div>
            )}

            {/* 추천 리스트 */}
            {loading && <p className="center muted mt16">불러오는 중...</p>}

            <div className="list mt12">
                {items.map((r) => (
                    <Link key={r.recipe_id} to={`/recipes/${r.recipe_id}`} className="card recipe-card-link">
                        <div className="card recipe-card">
                            {/* 대표 이미지 */}
                            <div className="recipe-image-placeholder">
                                {r.image_url ? (
                                    <img src={r.image_url} alt={r.title} className="recipe-image" />
                                ) : (
                                    <span>🍽️</span>
                                )}
                            </div>

                            <div className="row space-between">
                                <h3 className="recipe-title">{r.title}</h3>
                                <span className="pill">{r.cook_time_min || "?"}분</span>
                            </div>

                            {/* 추천 이유 */}
                            <div className="badge-wrap mt8">
                                {r.reasons?.slice(0, 3).map((reason, i) => (
                                    <span key={i} className="badge">
                                        {reason}
                                    </span>
                                ))}
                            </div>

                            {/* 부족 재료 */}
                            <p className="meta mt8">
                                부족 재료:{" "}
                                {r.missing_ingredients?.length
                                    ? r.missing_ingredients.slice(0, 3).join(", ")
                                    : "없음"}
                                {r.missing_ingredients?.length > 3 && ` +${r.missing_ingredients.length - 3}`}
                            </p>

                            {/* 장보기 목록 */}
                            {r.shopping_list && r.shopping_list.length > 0 && (
                                <details
                                    className="meta mt8 shopping-details"
                                    onClick={(e) => { e.stopPropagation(); }}
                                >
                                <summary onClick={(e) => e.stopPropagation()}>
                                    장보기 목록 ({r.shopping_list.length}개)
                                </summary>
                                    <ul className="shopping-list" onClick={(e) => { e.preventDefault(); e.stopPropagation(); }}>
                                        {r.shopping_list.map((item, i) => (
                                            <li key={i}>{item}</li>
                                        ))}
                                    </ul>
                                </details>
                            )}

                            {/* 재료 매칭률 (추천 모드에서만) */}
                            {!isSearchMode && r.coverage !== undefined && (
                                <p className="tiny muted mt4">
                                    재료 매칭률: {formatCoverage(r.coverage)}
                                    {r.missing_count > 0 && `, 부족: ${r.missing_count}개`}
                                </p>
                            )}

                            {/* 액션 버튼 */}
                            <div className="row space-between mt12 align-center">
                                <button
                                    type="button"
                                    className="btn"
                                    onClick={(e) => handleSave(e, r.recipe_id, r.title)}
                                >
                                    저장
                                </button>
                                <div className="row gap8">
                                    <button
                                        type="button"
                                        className="btn primary"
                                        onClick={(e) => {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            debouncedAction(r.recipe_id, "cook", r.title);
                                        }}
                                    >
                                        요리함
                                    </button>
                                    <button
                                        type="button"
                                        className="btn ghost"
                                        onClick={(e) => {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            debouncedAction(r.recipe_id, "skip", r.title);
                                        }}
                                    >
                                        스킵
                                    </button>
                                </div>
                            </div>
                        </div>
                    </Link>
                ))}
            </div>
        </div>
    );
}

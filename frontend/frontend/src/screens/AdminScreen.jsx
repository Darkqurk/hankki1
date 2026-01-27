import { useState, useEffect } from "react";
import { searchRecipes, getAdminRecipeDebug, getAdminStatus, getRecommendationConversion } from "../api";

const DEBUG_LABELS = {
    base: "기본점수",
    penalty_recent_cooked_saved: "최근 요리/저장 감점",
    penalty_recent_skipped: "최근 스킵 감점",
    penalty_cooldown: "최근 노출 감점",
    penalty_exposure_no_convert: "미전환 노출 감점",
    bonus_converted: "전환 보너스",
    exposure: "최근 노출 수",
    converted: "전환 여부",
    pop_users: "인기 사용자 수",
    pop_bonus: "인기 보너스",
};

export default function AdminScreen() {
    // ===== 통계 섹션 상태 =====
    const [statsLoading, setStatsLoading] = useState(true);
    const [statsError, setStatsError] = useState(null);
    const [adminStatus, setAdminStatus] = useState(null);
    const [conversionData, setConversionData] = useState(null);

    // ===== 기존 디버그 섹션 상태 (변경 없음) =====
    const [demoUser, setDemoUser] = useState(1);
    const [query, setQuery] = useState("");
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [expandedDebug, setExpandedDebug] = useState({});
    const [debugLoading, setDebugLoading] = useState({});

    // ===== 통계 데이터 로드 =====
    useEffect(() => {
        const loadStats = async () => {
            setStatsLoading(true);
            setStatsError(null);

            try {
                const [statusRes, convRes] = await Promise.allSettled([
                    getAdminStatus(),
                    getRecommendationConversion(7),
                ]);

                if (statusRes.status === "fulfilled") {
                    setAdminStatus(statusRes.value);
                }
                if (convRes.status === "fulfilled") {
                    setConversionData(convRes.value);
                }

                // 둘 다 실패한 경우만 에러 표시
                if (statusRes.status === "rejected" && convRes.status === "rejected") {
                    setStatsError("통계 데이터를 불러올 수 없습니다.");
                }
            } catch (e) {
                setStatsError("통계 로드 중 오류 발생");
            } finally {
                setStatsLoading(false);
            }
        };

        loadStats();
    }, []);

    // ===== 기존 디버그 로직 (변경 없음) =====
    const handleSearch = async () => {
        if (!query.trim()) return;
        setLoading(true);
        setExpandedDebug({});
        try {
            const data = await searchRecipes(query);
            setResults(data);
        } catch (e) {
            console.error("검색 실패:", e);
            setResults([]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === "Enter") handleSearch();
    };

    const toggleDebug = async (recipeId) => {
        if (!recipeId) {
            console.error("toggleDebug: recipeId가 없습니다.");
            return;
        }

        if (expandedDebug[recipeId]) {
            setExpandedDebug((prev) => {
                const next = { ...prev };
                delete next[recipeId];
                return next;
            });
            return;
        }

        setDebugLoading((prev) => ({ ...prev, [recipeId]: true }));
        try {
            const data = await getAdminRecipeDebug(recipeId, demoUser);
            setExpandedDebug((prev) => ({ ...prev, [recipeId]: data }));
        } catch (e) {
            console.error("디버그 조회 실패:", e);
            setExpandedDebug((prev) => ({
                ...prev,
                [recipeId]: { error: "조회 실패" },
            }));
        } finally {
            setDebugLoading((prev) => ({ ...prev, [recipeId]: false }));
        }
    };

    const renderDebugInfo = (data) => {
        if (data.error) {
            return <p style={{ color: "red" }}>{data.error}</p>;
        }

        return (
            <div className="admin-debug-detail">
                <div className="admin-debug-row">
                    <span className="admin-debug-label">총 점수</span>
                    <span className="admin-debug-value">{data.score}</span>
                </div>
                <div className="admin-debug-row">
                    <span className="admin-debug-label">커버리지</span>
                    <span className="admin-debug-value">{(data.coverage * 100).toFixed(1)}%</span>
                </div>
                <div className="admin-debug-row">
                    <span className="admin-debug-label">저장됨</span>
                    <span className="admin-debug-value">{data.saved ? "예" : "아니오"}</span>
                </div>

                {data.debug && (
                    <table className="admin-debug-table">
                        <thead>
                            <tr>
                                <th>항목</th>
                                <th>값</th>
                            </tr>
                        </thead>
                        <tbody>
                            {Object.entries(data.debug).map(([key, val]) => (
                                <tr key={key}>
                                    <td>{DEBUG_LABELS[key] || key}</td>
                                    <td>{typeof val === "boolean" ? (val ? "O" : "X") : val}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}

                {data.reasons && data.reasons.length > 0 && (
                    <div className="admin-debug-section">
                        <strong>추천 이유:</strong>
                        <ul>
                            {data.reasons.map((r, i) => <li key={i}>{r}</li>)}
                        </ul>
                    </div>
                )}

                {data.missing_ingredients && data.missing_ingredients.length > 0 && (
                    <div className="admin-debug-section">
                        <strong>부족 재료:</strong> {data.missing_ingredients.join(", ")}
                    </div>
                )}

                {data.shopping_list && data.shopping_list.length > 0 && (
                    <div className="admin-debug-section">
                        <strong>장보기 목록:</strong> {data.shopping_list.join(", ")}
                    </div>
                )}
            </div>
        );
    };

    // ===== KPI 카드 렌더 헬퍼 =====
    const renderKpiCard = (title, value, subtitle) => (
        <div style={{
            flex: "1 1 45%",
            minWidth: "140px",
            padding: "16px",
            border: "1px solid #e0e0e0",
            borderRadius: "8px",
            backgroundColor: "#fafafa",
        }}>
            <div style={{ fontSize: "12px", color: "#666", marginBottom: "4px" }}>{title}</div>
            <div style={{ fontSize: "24px", fontWeight: "bold", color: "#333" }}>
                {statsLoading ? (
                    <span style={{ display: "inline-block", width: "60px", height: "24px", backgroundColor: "#e0e0e0", borderRadius: "4px" }} />
                ) : value ?? "—"}
            </div>
            {subtitle && (
                <div style={{ fontSize: "11px", color: "#999", marginTop: "4px" }}>{subtitle}</div>
            )}
        </div>
    );

    return (
        <div className="admin-screen" style={{ padding: "16px" }}>
            {/* ===== 운영 통계 섹션 ===== */}
            <div style={{ marginBottom: "24px" }}>
                <h2 style={{ marginBottom: "12px" }}>운영 통계</h2>

                {statsError && (
                    <p style={{ fontSize: "12px", color: "#c00", marginBottom: "8px" }}>{statsError}</p>
                )}

                {/* KPI 카드 그리드 (2x2) */}
                <div style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: "12px",
                    marginBottom: "16px",
                }}>
                    {renderKpiCard(
                        "총 레시피 수",
                        adminStatus?.recipes_total?.toLocaleString(),
                        "서버 기준"
                    )}
                    {renderKpiCard(
                        "총 사용자 수",
                        adminStatus?.users?.toLocaleString(),
                        "등록된 계정"
                    )}
                    {renderKpiCard(
                        "Pantry 아이템",
                        adminStatus?.pantry_items?.toLocaleString(),
                        "전체 사용자 합계"
                    )}
                    {renderKpiCard(
                        "추천 전환율",
                        conversionData?.conversion_rate != null
                            ? `${(conversionData.conversion_rate * 100).toFixed(1)}%`
                            : null,
                        "최근 7일"
                    )}
                </div>

                {/* 추천 성능 요약 */}
                {conversionData && !statsLoading && (
                    <div style={{
                        padding: "12px",
                        backgroundColor: "#f5f5f5",
                        borderRadius: "6px",
                        fontSize: "13px",
                        color: "#555",
                    }}>
                        <strong>추천 성능 (최근 {conversionData.window_days || 7}일):</strong>{" "}
                        추천 노출 {conversionData.recommended_count ?? 0}건 중{" "}
                        {conversionData.converted_count ?? 0}건 전환 (조리/저장)
                    </div>
                )}

                {/* 확장 지표 Coming Soon */}
                <p style={{
                    fontSize: "11px",
                    color: "#aaa",
                    marginTop: "12px",
                    fontStyle: "italic",
                }}>
                    저장률/조리율/스킵률 등 action log 집계 기반 확장 지표는 추후 제공 예정
                </p>
            </div>

            <hr style={{ border: "none", borderTop: "1px solid #e0e0e0", margin: "24px 0" }} />

            {/* ===== 기존 관리자 디버그 섹션 (변경 없음) ===== */}
            <h2>관리자 디버그</h2>

            <div className="admin-user-select" style={{ marginBottom: "12px" }}>
                <label style={{ marginRight: "8px" }}>Demo 유저:</label>
                <button
                    className={demoUser === 1 ? "active" : ""}
                    onClick={() => { setDemoUser(1); setExpandedDebug({}); }}
                    style={{ marginRight: "4px", fontWeight: demoUser === 1 ? "bold" : "normal" }}
                >
                    demo1
                </button>
                <button
                    className={demoUser === 2 ? "active" : ""}
                    onClick={() => { setDemoUser(2); setExpandedDebug({}); }}
                    style={{ fontWeight: demoUser === 2 ? "bold" : "normal" }}
                >
                    demo2
                </button>
            </div>

            <div className="admin-search" style={{ marginBottom: "16px", display: "flex", gap: "8px" }}>
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="레시피 제목 검색..."
                    style={{ flex: 1, padding: "8px" }}
                />
                <button onClick={handleSearch} disabled={loading}>
                    {loading ? "검색중..." : "검색"}
                </button>
            </div>

            {results.length === 0 && !loading && (
                <p style={{ color: "#888" }}>검색 결과가 없습니다.</p>
            )}

            <div className="admin-results">
                {results.map((item) => (
                    <div key={item.recipe_id} className="admin-recipe-card" style={{
                        border: "1px solid #ddd",
                        borderRadius: "8px",
                        padding: "12px",
                        marginBottom: "12px",
                    }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <div>
                                <strong>{item.title}</strong>
                                {item.cook_time_min && (
                                    <span style={{ marginLeft: "8px", color: "#666" }}>
                                        {item.cook_time_min}분
                                    </span>
                                )}
                                <span style={{ marginLeft: "8px", color: "#999", fontSize: "12px" }}>
                                    ID: {item.recipe_id}
                                </span>
                            </div>
                            <button
                                onClick={(e) => { e.stopPropagation(); toggleDebug(item.recipe_id); }}
                                disabled={debugLoading[item.recipe_id]}
                                style={{ fontSize: "13px" }}
                            >
                                {debugLoading[item.recipe_id]
                                    ? "로딩..."
                                    : expandedDebug[item.recipe_id]
                                        ? "디버그 닫기"
                                        : "디버그 보기"}
                            </button>
                        </div>

                        {expandedDebug[item.recipe_id] && (
                            <div style={{ marginTop: "12px", borderTop: "1px solid #eee", paddingTop: "12px" }}>
                                {renderDebugInfo(expandedDebug[item.recipe_id])}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}

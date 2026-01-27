import { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import { getUserRecipes, deleteUserRecipe } from "../api";
import AddRecipe from "../components/AddRecipe";

export default function MyRecipesScreen() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);
    const [query, setQuery] = useState("");
    const debounceRef = useRef(null);

    const load = async (q = "") => {
        setLoading(true);
        try {
            const data = await getUserRecipes(q);
            setItems(data);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, []);

    // 검색어 변경 시 디바운스 적용
    const handleQueryChange = (e) => {
        const value = e.target.value;
        setQuery(value);

        if (debounceRef.current) {
            clearTimeout(debounceRef.current);
        }

        debounceRef.current = setTimeout(() => {
            load(value.trim());
        }, 300);
    };

    const handleDelete = async (e, recipeId) => {
        e.preventDefault();
        e.stopPropagation();
        if (confirm("레시피를 삭제하시겠습니까?")) {
            await deleteUserRecipe(recipeId);
            alert("레시피 삭제 완료!");
            await load(query); // 목록 새로고침 (검색 상태 유지)
        }
    };

    return (
        <div className="page">
            {/* 레시피 추가 */}
            <AddRecipe onSuccess={() => load(query)} />

            {/* 내 레시피 목록 */}
            <h2 className="title mt16">등록한 레시피 목록</h2>

            {/* 검색 입력 */}
            <input
                className="input mt12"
                placeholder="레시피 제목 검색..."
                value={query}
                onChange={handleQueryChange}
            />

            {loading && <p className="center muted mt16">불러오는 중...</p>}

            {!loading && items.length === 0 && (
                <p className="center muted mt16">등록된 레시피가 없습니다.</p>
            )}

            <div className="list mt12">
                {items.map((r) => (
                    <div key={r.id} className="card recipe-card"> {/* recipe_id -> id */}
                        <Link to={`/recipes/${r.id}`} className="recipe-card-link"> {/* recipe_id -> id */}
                            <div className="recipe-image-placeholder">
                                {(r.thumbnail_url || r.image_url) ? (
                                    <img src={r.thumbnail_url || r.image_url} alt={r.title} className="recipe-image" />
                                ) : (
                                    <span>🍽️</span>
                                )}
                            </div>
                            <div className="row space-between">
                                <h3 className="recipe-title">{r.title}</h3>
                                <span className="pill">{r.cook_time_min || "?"}분</span>
                            </div>
                        </Link>
                        
                        <div className="row space-between mt8 align-center">
                            {r.is_public ? (
                                <span className="badge">공개 레시피</span>
                            ) : (
                                <span className="badge" style={{ backgroundColor: "#ffefd5", color: "#ffa500" }}>비공개 레시피</span>
                            )}
                            <div className="row gap8">
                                <button className="btn ghost">수정</button> {/* 수정 버튼 (placeholder) */}
                                <button 
                                    className="btn ghost" 
                                    onClick={(e) => handleDelete(e, r.id)} // recipe_id -> id
                                >
                                    삭제
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

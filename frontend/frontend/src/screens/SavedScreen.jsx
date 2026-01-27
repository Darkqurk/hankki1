import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getSavedRecipes, unsaveRecipe } from "../api";

export default function SavedScreen() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);

    const load = async () => {
        setLoading(true);
        try {
            const data = await getSavedRecipes();
            setItems(data);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, []);

    const handleUnsave = async (e, recipeId) => {
        e.preventDefault();
        e.stopPropagation();
        if (confirm("저장함에서 삭제하시겠습니까?")) {
            await unsaveRecipe(recipeId);
            await load(); // 목록 새로고침
        }
    };

    return (
        <div className="page">
            <div className="card header-card">
                <h2 className="title">저장한 레시피</h2>
                <p className="sub">다시 보고 싶은 레시피를 저장해두세요.</p>
            </div>

            {loading && <p className="center muted mt16">불러오는 중...</p>}

            {!loading && items.length === 0 && (
                <p className="center muted mt16">저장된 레시피가 없습니다.</p>
            )}

            <div className="list mt12">
                {items.map((r) => (
                    <div key={r.recipe_id} className="card recipe-card">
                        <Link to={`/recipes/${r.recipe_id}`} className="recipe-card-link">
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
                        </Link>
                        <div className="row space-between mt12 align-center">
                            <span></span>
                            <button
                                className="btn ghost"
                                onClick={(e) => handleUnsave(e, r.recipe_id)}
                            >
                                저장 취소
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
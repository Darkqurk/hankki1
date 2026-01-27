import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getRecipeById, saveRecipe, unsaveRecipe, recipeAction } from "../api";

const PLACEHOLDER_IMAGE = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'%3E%3Crect fill='%23E5E8EB' width='400' height='300'/%3E%3Ctext x='50%25' y='45%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='48' fill='%23B0B8C1'%3E🍽️%3C/text%3E%3Ctext x='50%25' y='60%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='14' fill='%236B7684'%3E이미지 없음%3C/text%3E%3C/svg%3E";

export default function RecipeDetailPage() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [recipe, setRecipe] = useState(null);
    const [loading, setLoading] = useState(false);
    const [isSaved, setIsSaved] = useState(false);

    const loadRecipe = async () => {
        setLoading(true);
        try {
            const data = await getRecipeById(id);
            setRecipe(data);
            setIsSaved(data.is_saved);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadRecipe();
    }, [id]);

    const handleSaveToggle = async () => {
        if (isSaved) {
            await unsaveRecipe(id);
        } else {
            await saveRecipe(id);
        }
        setIsSaved(!isSaved);
    };

    const handleAction = async (action) => {
        await recipeAction(id, action);
        navigate("/"); // Or show a confirmation
    };

    if (loading) {
        return <div className="page center">로딩중...</div>;
    }

    if (!recipe) {
        return <div className="page center">레시피를 찾을 수 없습니다.</div>;
    }

    const steps = Array.isArray(recipe?.steps) ? recipe.steps.filter(Boolean) : [];

    return (
        <div className="page recipe-detail-page">
            <div className="header">
                <button onClick={() => navigate(-1)} className="back-btn">←</button>
            </div>
            <div className="card">
                <img
                    src={recipe.image_url || PLACEHOLDER_IMAGE}
                    alt={recipe.title}
                    className="recipe-hero-image"
                    />
                <h2 className="title mt16">{recipe.title}</h2>

                <div className="badge-wrap mt8">
                    {recipe.reasons?.map((reason, i) => (
                        <span key={i} className="badge">
                            {reason}
                        </span>
                    ))}
                </div>

                <h3 className="mt16">재료</h3>
                <div className="ingredients-box mt8">
                    {recipe.raw_ingredients}
                </div>


                <h3 className="mt16">만드는 방법</h3>
                <ol className="list-decimal mt8 pl20">
                    {steps.map((step, index) => {
                        // 업로드 이미지(step_image_url) 우선, 없으면 외부 URL(image_url)
                        const stepImg = step.step_image_url || step.image_url;
                        return (
                            <li key={step.step_no ?? index + 1} className="mb12">
                                <p>{step.description}</p>
                                {stepImg && (
                                <img
                                    src={stepImg}
                                    alt={`Step ${step.step_no}`}
                                    className="recipe-step-image mt8"
                                />
                                )}
                            </li>
                        );
                    })}
                </ol>

                {recipe.source && (
                    <div className="source-box mt16">
                       출처: {recipe.source}
                    </div>
                )}
            </div>

            <div className="cta-bar">
                <button className={`btn ${isSaved ? '' : 'primary'}`} onClick={handleSaveToggle}>
                    {isSaved ? '저장해제' : '저장'}
                </button>
                <button className="btn primary" onClick={() => handleAction('cook')}>
                    요리함
                </button>
                <button className="btn ghost" onClick={() => handleAction('skip')}>
                    스킵
                </button>
            </div>
        </div>
    );
}

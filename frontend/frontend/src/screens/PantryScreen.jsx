import { useEffect, useState } from "react";
import { getPantry, addPantryItem, deletePantryItem } from "../api";

export default function PantryScreen({ onPantryChanged }) {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);
    
    // 새 재료 입력을 위한 상태
    const [newItemName, setNewItemName] = useState("");
    const [newItemQuantity, setNewItemQuantity] = useState("");
    const [newItemUnit, setNewItemUnit] = useState("개");
    const [newItemExpiresAt, setNewItemExpiresAt] = useState(""); // "YYYY-MM-DD"


    const load = async () => {
        setLoading(true);
        try {
            const data = await getPantry();
            setItems(data);
        } finally { 
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, []);

    const handleAddItem = async (e) => {
    e.preventDefault();

    const name = (newItemName || "").trim();
    const qty = (newItemQuantity || "").toString().trim();
    const unit = (newItemUnit || "").trim();
    const exp = (newItemExpiresAt || "").trim();

    if (!name) {
        alert("재료 이름을 입력해주세요.");
        return;
    }
    if (!qty) {
        alert("수량을 입력해주세요.");
        return;
    }

    // 백엔드가 quantity_text를 받으므로 "2개" 형태로 문자열 합치기
    const quantityText = unit ? `${qty}${unit}` : qty;

    const payload = {
        ingredient_name: name,            // ✅ 키 이름 고정
        quantity_text: quantityText,      // ✅ 문자열
        expires_at: exp ? exp : null,     // ✅ ""이면 null
    };

    try {
        await addPantryItem(payload);
        setNewItemName("");
        setNewItemQuantity("");
        setNewItemExpiresAt("");
        // unit은 유지하고 싶으면 그대로 두고, 초기화하고 싶으면 아래 켜기
        // setNewItemUnit("개");

        await load(); // 목록 갱신
        onPantryChanged?.(); // 추천 리스트 갱신 트리거
    } catch (err) {
        console.log("pantry POST error:", err?.response?.data || err);
        alert(
        JSON.stringify(
            err?.response?.data || { error: err.message },
            null,
            2
        )
        );
    }
    };


    const handleDeleteItem = async (id) => {
        if (confirm("재료를 삭제하시겠습니까?")) {
            await deletePantryItem(id);
            await load(); // 목록 새로고침
            onPantryChanged?.(); // 추천 리스트 갱신 트리거
        }
    };

    return (
        <div className="page">
            {/* 재료 추가 폼 */}
            <div className="card">
                <h2 className="title">냉장고 재료 추가</h2>
                <form onSubmit={handleAddItem} className="mt12">
                    <div className="row gap8">
                        <input 
                            type="text" 
                            value={newItemName}
                            onChange={(e) => setNewItemName(e.target.value)}
                            placeholder="재료 이름 (예: 계란)" 
                            className="input flex-grow"
                        />
                        <input 
                            type="number" 
                            value={newItemQuantity}
                            onChange={(e) => setNewItemQuantity(e.target.value)}
                            placeholder="수량" 
                            className="input"
                            style={{ width: '60px' }}
                        />
                        <select 
                            value={newItemUnit}
                            onChange={(e) => setNewItemUnit(e.target.value)}
                            className="select"
                        >
                            <option>개</option>
                            <option>g</option>
                            <option>ml</option>
                            <option>큰술</option>
                            <option>작은술</option>
                        </select>
                        <input
                            type="date"
                            value={newItemExpiresAt}
                            onChange={(e) => setNewItemExpiresAt(e.target.value)}
                            className="input"
                            style={{ width: "140px" }}
                            />
                        <button type="submit" className="btn primary">추가</button>
                    </div>
                </form>
            </div>

            {/* 재료 목록 */}
            <div className="card mt16">
                <h2 className="title">내 냉장고</h2>
                {loading && <p className="center muted mt16">불러오는 중...</p>}
                
                {!loading && items.length === 0 && (
                    <p className="center muted mt16">냉장고에 재료가 없습니다.</p>
                )}

                <ul className="pantry-list mt12">
                    {items.map((item) => (
                        <li key={item.id} className="pantry-item">
                            <span className="pantry-item-name">{item.ingredient_name}</span>
                            <span className="pantry-item-quantity">{item.quantity_text}</span>
                            {item.expires_at && (
                                <span className="pantry-item-expires">~{item.expires_at}</span>
                            )}
                            <button
                                onClick={() => handleDeleteItem(item.id)}
                                className="btn-delete"
                            >
                                ×
                            </button>
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    );
}
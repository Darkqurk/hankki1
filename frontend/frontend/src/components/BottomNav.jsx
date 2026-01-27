export default function BottomNav({ activeTab, setActiveTab, isAdmin, nickname, onLogout }) {
    // 일반 사용자 탭
    const userTabs = [
        { id: "recommend", label: "추천" },
        { id: "saved", label: "저장함" },
        { id: "pantry", label: "냉장고" },
        { id: "my", label: "내 레시피" },
    ];

    // Admin인 경우 관리자 탭 추가
    const tabs = isAdmin
        ? [...userTabs, { id: "admin", label: "관리자" }]
        : userTabs;

    return (
        <div className="bottom-nav">
            {tabs.map((tab) => (
                <button
                    key={tab.id}
                    className={`nav-btn ${activeTab === tab.id ? "active" : ""}`}
                    onClick={() => setActiveTab(tab.id)}
                >
                    {tab.label}
                </button>
            ))}

            {/* 로그아웃 버튼 */}
            <button
                className="nav-btn logout-btn"
                onClick={onLogout}
                style={{
                    fontSize: "12px",
                    color: "#999",
                }}
                title={nickname ? `${nickname} 로그아웃` : "로그아웃"}
            >
                로그아웃
            </button>
        </div>
    );
}

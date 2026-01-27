import { useState } from "react";
import { Routes, Route, useLocation } from "react-router-dom";

// Screens
import LoginScreen from "./screens/LoginScreen";
import RecommendScreen from "./screens/RecommendScreen";
import RecipeDetailPage from "./screens/RecipeDetailPage";
import SavedScreen from "./screens/SavedScreen";
import PantryScreen from "./screens/PantryScreen";
import MyRecipesScreen from "./screens/MyRecipesScreen";
import AdminScreen from "./screens/AdminScreen";

// Components
import BottomNav from "./components/BottomNav";

// Hooks
import useTossAuth from "./hooks/useTossAuth";

import "./App.css";

function App() {
  const [activeTab, setActiveTab] = useState("recommend");
  const location = useLocation();

  // 토스 인앱 로그인 상태 관리
  const auth = useTossAuth();

  // 냉장고 재료 변경 시 추천 리스트 갱신용 카운터
  const [pantryRev, setPantryRev] = useState(0);
  const bumpPantryRev = () => setPantryRev((v) => v + 1);

  // 상세 페이지에서는 탭 네비게이션을 숨깁니다.
  const showBottomNav = location.pathname === "/";

  // =====================================
  // 로그인 로딩 중
  // =====================================
  if (auth.loading) {
    return (
      <div className="app-container" style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        flexDirection: "column",
        gap: "12px",
      }}>
        <div style={{ fontSize: "32px" }}>🍳</div>
        <p style={{ color: "#666" }}>로그인 확인 중...</p>
      </div>
    );
  }

  // =====================================
  // 로그인 안 됨 → 로그인 화면
  // =====================================
  if (!auth.loggedIn) {
    return (
      <LoginScreen
        isTossApp={auth.isTossApp}
        onLoginSuccess={() => auth.refresh()}
      />
    );
  }

  // =====================================
  // 로그인 됨 → 메인 앱
  // =====================================
  const renderContent = () => {
    switch (activeTab) {
      case "recommend":
        return <RecommendScreen pantryRev={pantryRev} />;
      case "saved":
        return <SavedScreen />;
      case "pantry":
        return <PantryScreen onPantryChanged={bumpPantryRev} />;
      case "my":
        return <MyRecipesScreen />;
      case "admin":
        // Admin 탭은 isAdmin인 경우에만 실제 내용 렌더
        return auth.isAdmin ? <AdminScreen /> : <RecommendScreen pantryRev={pantryRev} />;
      default:
        return <RecommendScreen pantryRev={pantryRev} />;
    }
  };

  return (
    <div className="app-container">
      <Routes>
        <Route path="/" element={renderContent()} />
        <Route path="/recipes/:id" element={<RecipeDetailPage />} />
      </Routes>

      {showBottomNav && (
        <BottomNav
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          isAdmin={auth.isAdmin}
          nickname={auth.nickname}
          onLogout={auth.logout}
        />
      )}
    </div>
  );
}

export default App;

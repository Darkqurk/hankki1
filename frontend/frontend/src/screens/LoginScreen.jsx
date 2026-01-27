import { useState } from "react";
import { demoLogin } from "../api";

/**
 * 로그인 화면
 * - 토스 인앱 로그인 (실제 토스 앱 환경에서만 동작)
 * - 데모 계정 로그인 (발표용)
 */
export default function LoginScreen({ onLoginSuccess, isTossApp }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // =============================================
    // 공통 데모 로그인 처리 함수
    // =============================================
    const performDemoLogin = async (type) => {
        // 이미 로딩 중이면 중복 실행 방지
        if (loading) return;

        setLoading(true);
        setError(null);

        console.log(`[LoginScreen] 데모 로그인 시작: ${type}`);

        try {
            // 1. 백엔드 데모 로그인 API 호출
            const result = await demoLogin(type);
            console.log("[LoginScreen] demoLogin 응답:", result);

            if (!result.ok) {
                throw new Error(result.error || "로그인 실패");
            }

            // 2. 로그인 성공 → 상태 갱신 (완료까지 대기!)
            console.log("[LoginScreen] onLoginSuccess 호출 시작");

            // ✅ 핵심: await로 refresh() 완료를 기다림
            if (onLoginSuccess) {
                await onLoginSuccess();
            }

            console.log("[LoginScreen] onLoginSuccess 완료 → 화면 전환 예정");

            // 이 시점에서 App.jsx의 auth.loggedIn이 true가 되어
            // 자동으로 메인 화면으로 전환됨

        } catch (err) {
            console.error("[LoginScreen] 로그인 에러:", err);
            setError(err.message || "로그인 중 오류가 발생했습니다.");
            setLoading(false);  // 에러 시에만 여기서 loading 해제
        }
        // ✅ 성공 시에는 loading을 해제하지 않음
        // → App.jsx가 메인 화면으로 전환하면서 이 컴포넌트가 언마운트됨
    };

    // 데모 사용자 로그인
    const handleDemoUserLogin = () => performDemoLogin("user");

    // 데모 관리자 로그인
    const handleDemoAdminLogin = () => performDemoLogin("admin");

    // 토스 인앱 로그인
    const handleTossLogin = async () => {
        if (!isTossApp) {
            setError("토스 앱 환경에서만 사용 가능합니다.");
            return;
        }

        if (loading) return;
        setLoading(true);
        setError(null);

        try {
            if (window.TossAppBridge) {
                window.TossAppBridge.appLogin({
                    success: async () => {
                        console.log("[LoginScreen] 토스 로그인 성공");
                        if (onLoginSuccess) {
                            await onLoginSuccess();
                        }
                    },
                    fail: (err) => {
                        console.error("[LoginScreen] 토스 로그인 실패:", err);
                        setError(err.message || "토스 로그인 실패");
                        setLoading(false);
                    },
                });
            } else {
                throw new Error("토스 앱 환경이 아닙니다.");
            }
        } catch (err) {
            setError(err.message);
            setLoading(false);
        }
    };

    return (
        <div className="page login-screen">
            {/* 로고/타이틀 영역 */}
            <div className="login-header">
                <h1 className="login-title">
                    한끼
                </h1>
                <p className="login-subtitle">
                    냉장고 재료로 뚝딱 레시피 추천
                </p>
            </div>

            {/* 로그인 버튼들 */}
            <div className="login-btn-group">
                {/* 토스 로그인 버튼 */}
                <button
                    onClick={handleTossLogin}
                    disabled={loading || !isTossApp}
                    className="btn-toss-primary"
                >
                    {loading ? "로그인 중..." : "토스로 시작하기"}
                </button>

                {!isTossApp && (
                    <p className="login-toss-notice">
                        토스 앱 환경에서 사용 가능
                    </p>
                )}

                {/* 구분선 */}
                <div className="login-divider">
                    <span className="login-divider-text">또는</span>
                </div>

                {/* 데모 사용자 로그인 */}
                <button
                    onClick={handleDemoUserLogin}
                    disabled={loading}
                    className="btn-toss-secondary"
                >
                    {loading ? "로그인 중..." : "데모 계정으로 시작"}
                </button>

                {/* 데모 관리자 로그인 */}
                <button
                    onClick={handleDemoAdminLogin}
                    disabled={loading}
                    className="btn-toss-tertiary"
                >
                    {loading ? "로그인 중..." : "관리자 데모 (개발용)"}
                </button>
            </div>

            {/* 에러 메시지 */}
            {error && (
                <p className="login-error-msg">
                    {error}
                </p>
            )}

            {/* 하단 안내 */}
            <p className="login-footer-notice">
                데모 계정은 발표/테스트 용도입니다.<br />
                실제 서비스에서는 토스 로그인을 사용합니다.
            </p>
        </div>
    );
}
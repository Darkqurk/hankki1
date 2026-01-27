import { useState, useEffect, useCallback } from "react";
import { tossLogin, getAuthStatus, logout as apiLogout } from "../api";

/**
 * 토스 인앱 환경 감지 및 로그인 처리 훅
 *
 * 반환값:
 * - loading: 로그인 상태 확인 중
 * - loggedIn: 로그인 여부
 * - tossUserId: 토스 유저 ID
 * - nickname: 유저 닉네임
 * - isAdmin: 관리자 여부
 * - isTossApp: 토스 앱 환경 여부
 * - error: 에러 메시지
 * - refresh: 로그인 상태 재확인
 * - logout: 로그아웃
 */
export default function useTossAuth() {
  const [authState, setAuthState] = useState({
    loading: true,
    loggedIn: false,
    tossUserId: null,
    nickname: null,
    isAdmin: false,
    error: null,
    isTossApp: false,
  });

  // 토스 인앱 환경 감지
  const detectTossApp = useCallback(() => {
    const ua = navigator.userAgent || "";
    if (ua.includes("TossApp") || ua.includes("toss")) {
      return true;
    }
    if (typeof window !== "undefined" && window.TossAppBridge) {
      return true;
    }
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("toss") === "1") {
      return true;
    }
    return false;
  }, []);

  // 토스 SDK appLogin 호출
  const callTossAppLogin = useCallback(async () => {
    return new Promise((resolve, reject) => {
      if (typeof window === "undefined" || !window.TossAppBridge) {
        if (process.env.NODE_ENV === "development") {
          reject(new Error("TossAppBridge not available in dev"));
          return;
        }
        reject(new Error("TossAppBridge not available"));
        return;
      }

      try {
        window.TossAppBridge.appLogin({
          success: (result) => {
            resolve({
              authorizationCode: result.authorizationCode,
              referrer: result.referrer || window.location.href,
            });
          },
          fail: (error) => {
            reject(new Error(error.message || "appLogin failed"));
          },
        });
      } catch (err) {
        reject(err);
      }
    });
  }, []);

  // 로그인 상태 확인
  const checkAuthStatus = useCallback(async () => {
    try {
      const status = await getAuthStatus();
      return {
        loggedIn: status.logged_in,
        tossUserId: status.toss_user_id,
        nickname: status.nickname,
        isAdmin: status.is_admin,
      };
    } catch (err) {
      return {
        loggedIn: false,
        tossUserId: null,
        nickname: null,
        isAdmin: false,
      };
    }
  }, []);

  // 초기화: 토스 환경 감지 → 로그인 상태 확인
  const initAuth = useCallback(async () => {
    const isTossApp = detectTossApp();
    setAuthState((prev) => ({ ...prev, loading: true, isTossApp }));

    // 먼저 기존 세션 상태 확인
    const status = await checkAuthStatus();

    if (status.loggedIn) {
      // 이미 로그인된 상태
      setAuthState({
        loading: false,
        loggedIn: true,
        tossUserId: status.tossUserId,
        nickname: status.nickname,
        isAdmin: status.isAdmin,
        error: null,
        isTossApp,
      });
      return;
    }

    // 토스 앱이 아니면 로그인 안 된 상태로 유지
    if (!isTossApp) {
      setAuthState({
        loading: false,
        loggedIn: false,
        tossUserId: null,
        nickname: null,
        isAdmin: false,
        error: null,
        isTossApp: false,
      });
      return;
    }

    // 토스 앱인 경우: appLogin 시도
    try {
      const { authorizationCode, referrer } = await callTossAppLogin();
      const loginResult = await tossLogin(authorizationCode, referrer);

      if (loginResult.ok) {
        setAuthState({
          loading: false,
          loggedIn: true,
          tossUserId: loginResult.toss_user_id,
          nickname: loginResult.nickname || null,
          isAdmin: loginResult.is_admin || false,
          error: null,
          isTossApp: true,
        });
      } else {
        throw new Error(loginResult.error || "Login failed");
      }
    } catch (err) {
      console.error("[useTossAuth] 토스 로그인 실패:", err);
      setAuthState({
        loading: false,
        loggedIn: false,
        tossUserId: null,
        nickname: null,
        isAdmin: false,
        error: err.message,
        isTossApp,
      });
    }
  }, [detectTossApp, callTossAppLogin, checkAuthStatus]);

  // 로그아웃
  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch (err) {
      console.error("[useTossAuth] 로그아웃 실패:", err);
    }
    setAuthState({
      loading: false,
      loggedIn: false,
      tossUserId: null,
      nickname: null,
      isAdmin: false,
      error: null,
      isTossApp: authState.isTossApp,
    });
  }, [authState.isTossApp]);

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  return {
    ...authState,
    refresh: initAuth,
    logout,
  };
}

import axios from "axios";

export const api = axios.create({
  baseURL: "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
  withCredentials: true, // 세션 쿠키 전송 (토스 로그인 후 유저 유지용)
});

// ===== 토스 인앱 로그인 관련 =====
export const tossLogin = (authorizationCode, referrer) =>
  api
    .post("/api/auth/toss/login/", { authorizationCode, referrer })
    .then((r) => r.data);

export const getAuthStatus = () =>
  api.get("/api/auth/status/").then((r) => r.data);

export const logout = () =>
  api.post("/api/auth/logout/").then((r) => r.data);

// 발표용 데모 로그인
export const demoLogin = (demoUser = "user") =>
  api.post("/api/auth/demo/login/", { demo_user: demoUser }).then((r) => r.data);

// 추천
export const getRecommendations = (top = 5) =>
  api.get(`/api/recommendations/recipes/?top=${top}`).then((r) => r.data);

// 레시피 상세 조회
export const getRecipeById = (recipeId) =>
  api.get(`/api/recipes/${recipeId}/`).then((r) => r.data);

// 저장/해제
export const saveRecipe = (recipeId) =>
  api.post("/api/recipes/save/", { recipe_id: recipeId }).then((r) => r.data);

export const unsaveRecipe = (recipeId) =>
  api.post("/api/recipes/unsave/", { recipe_id: recipeId }).then((r) => r.data);

// 저장함 목록
export const getSavedRecipes = () =>
  api.get("/api/recipes/saved/").then((r) => r.data);

// 레시피 액션 (cook/save/skip) - 추천 로직 학습용 로그
export const recipeAction = (recipeId, action) =>
  api
    .post("/api/recipes/action/", { recipe_id: recipeId, action })
    .then((r) => r.data);

// 팬트리
export const getPantry = () => api.get("/api/pantry/").then((r) => r.data);

export const addPantryItem = (payload) =>
  api.post("/api/pantry/", payload).then((r) => r.data);

export const updatePantryItem = (id, payload) =>
  api.patch(`/api/pantry/${id}/`, payload).then((r) => r.data);

export const deletePantryItem = (id) =>
  api.delete(`/api/pantry/${id}/`).then((r) => r.data);

// 사용자 레시피 생성 (JSON - deprecated, 호환용)
export const createUserRecipe = (payload) =>
  api.post("/api/recipes/user/", payload).then((r) => r.data);

/**
 * 사용자 레시피 생성 (FormData - 이미지 업로드 지원)
 * @param {Object} data - { title, cookTimeMin, ingredients, isPublic, steps, thumbnailFile, stepImages }
 * @returns {Promise}
 */
export const createUserRecipeWithImages = async (data) => {
  const formData = new FormData();

  // 텍스트 필드
  formData.append("title", data.title || "");
  formData.append("cook_time_min", data.cookTimeMin || "");
  formData.append("ingredients", data.ingredients || ""); // 콤마 구분 문자열
  formData.append("is_public", data.isPublic ? "true" : "false");

  // steps JSON (설명만 포함)
  const stepsJson = (data.steps || []).map((s, i) => ({
    step_no: i + 1,
    description: s.description || "",
  }));
  formData.append("steps_json", JSON.stringify(stepsJson));

  // 썸네일 파일
  if (data.thumbnailFile) {
    formData.append("thumbnail", data.thumbnailFile);
  }

  // 단계별 이미지 파일
  (data.steps || []).forEach((step, idx) => {
    if (step.imageFile) {
      formData.append(`step_image_${idx}`, step.imageFile);
    }
  });

  // multipart/form-data 전송 (Content-Type 헤더 자동 설정)
  return api
    .post("/api/recipes/user/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

// 사용자 레시피 목록 (검색 지원)
export const getUserRecipes = (q = "") => {
  const params = q ? { q } : {};
  return api.get("/api/recipes/user/", { params }).then((r) => r.data);
};

// 사용자 레시피 삭제
export const deleteUserRecipe = (recipeId) =>
  api.delete(`/api/recipes/user/${recipeId}/`).then((r) => r.data);

// 외부 레시피 시드
export const seedExternalRecipes = (limit = 30, query = "계란") =>
  api
    .post("/external/recipes/seed/", { limit, query })
    .then((r) => r.data);

// 레시피 검색 (제목 기준)
export const searchRecipes = (q) =>
  api.get("/api/recipes/search/", { params: { q } }).then((r) => r.data);

// 관리자 디버그: 특정 레시피의 추천 점수/디버그 조회
export const getAdminRecipeDebug = (recipeId, demoUser) =>
  api.get("/api/admin/recipe-debug/", { params: { recipe_id: recipeId, demo_user: demoUser } }).then((r) => r.data);

// 관리자 통계: 서버 상태 조회
export const getAdminStatus = () =>
  api.get("/api/admin/status/").then((r) => r.data);

// 추천 전환율 통계 조회
export const getRecommendationConversion = (days = 7) =>
  api.get("/api/recommendations/conversion/", { params: { days } }).then((r) => r.data);

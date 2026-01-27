import { useState, useRef } from "react";
import { createUserRecipeWithImages } from "../api";

export default function AddRecipe({ onSuccess }) {
  const [title, setTitle] = useState("");
  const [cookTime, setCookTime] = useState("");
  const [ingredients, setIngredients] = useState("");
  const [isPublic, setIsPublic] = useState(true);
  const [loading, setLoading] = useState(false);

  // 썸네일 파일 상태
  const [thumbnailFile, setThumbnailFile] = useState(null);
  const [thumbnailPreview, setThumbnailPreview] = useState(null);
  const thumbnailInputRef = useRef(null);

  // 조리 단계 상태 (기본 1개)
  const [steps, setSteps] = useState([{ description: "", imageFile: null, imagePreview: null }]);

  // 썸네일 파일 선택 핸들러
  const handleThumbnailChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setThumbnailFile(file);
      // 미리보기 생성
      const reader = new FileReader();
      reader.onloadend = () => setThumbnailPreview(reader.result);
      reader.readAsDataURL(file);
    }
  };

  // 썸네일 삭제
  const removeThumbnail = () => {
    setThumbnailFile(null);
    setThumbnailPreview(null);
    if (thumbnailInputRef.current) {
      thumbnailInputRef.current.value = "";
    }
  };

  // 단계 추가
  const addStep = () => {
    setSteps([...steps, { description: "", imageFile: null, imagePreview: null }]);
  };

  // 단계 삭제 (최소 1개 유지)
  const removeStep = (index) => {
    if (steps.length <= 1) return;
    setSteps(steps.filter((_, i) => i !== index));
  };

  // 단계 설명 수정
  const updateStepDescription = (index, value) => {
    const newSteps = [...steps];
    newSteps[index] = { ...newSteps[index], description: value };
    setSteps(newSteps);
  };

  // 단계 이미지 선택 핸들러
  const handleStepImageChange = (index, e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        const newSteps = [...steps];
        newSteps[index] = {
          ...newSteps[index],
          imageFile: file,
          imagePreview: reader.result,
        };
        setSteps(newSteps);
      };
      reader.readAsDataURL(file);
    }
  };

  // 단계 이미지 삭제
  const removeStepImage = (index) => {
    const newSteps = [...steps];
    newSteps[index] = {
      ...newSteps[index],
      imageFile: null,
      imagePreview: null,
    };
    setSteps(newSteps);
  };

  const submit = async () => {
    if (!title.trim()) {
      alert("레시피 제목을 입력해주세요.");
      return;
    }
    if (!ingredients.trim()) {
      alert("재료를 입력해주세요.");
      return;
    }

    // 유효한 steps만 필터링 (description이 있는 것만)
    const validSteps = steps.filter((s) => s.description.trim());

    setLoading(true);
    try {
      await createUserRecipeWithImages({
        title: title.trim(),
        cookTimeMin: cookTime,
        ingredients: ingredients.trim(),
        isPublic,
        thumbnailFile,
        steps: validSteps,
      });

      alert("레시피 등록 완료!");

      // 초기화
      setTitle("");
      setCookTime("");
      setIngredients("");
      setIsPublic(true);
      setThumbnailFile(null);
      setThumbnailPreview(null);
      setSteps([{ description: "", imageFile: null, imagePreview: null }]);
      if (thumbnailInputRef.current) {
        thumbnailInputRef.current.value = "";
      }

      onSuccess?.();
    } catch (e) {
      console.error("레시피 등록 에러:", e);
      alert("에러: " + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h3 className="title">내 레시피 추가</h3>

      <input
        className="input mt12"
        placeholder="레시피 제목"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />

      <input
        className="input mt12"
        type="number"
        placeholder="조리 시간 (분)"
        value={cookTime}
        onChange={(e) => setCookTime(e.target.value)}
      />

      <input
        className="input mt12"
        placeholder="재료 (콤마로 구분: 계란, 소금, 대파)"
        value={ingredients}
        onChange={(e) => setIngredients(e.target.value)}
      />

      {/* 썸네일 이미지 업로드 */}
      <div className="mt12">
        <label style={{ fontSize: "14px", fontWeight: 600, display: "block", marginBottom: "6px" }}>
          썸네일 이미지 (선택)
        </label>
        <input
          ref={thumbnailInputRef}
          type="file"
          accept="image/*"
          onChange={handleThumbnailChange}
          style={{ fontSize: "13px" }}
        />
        {thumbnailPreview && (
          <div style={{ marginTop: "8px", position: "relative", display: "inline-block" }}>
            <img
              src={thumbnailPreview}
              alt="썸네일 미리보기"
              style={{
                maxWidth: "150px",
                maxHeight: "150px",
                borderRadius: "8px",
                border: "1px solid #ddd",
              }}
            />
            <button
              type="button"
              onClick={removeThumbnail}
              style={{
                position: "absolute",
                top: "-8px",
                right: "-8px",
                width: "24px",
                height: "24px",
                borderRadius: "50%",
                background: "#ff6b6b",
                color: "#fff",
                border: "none",
                cursor: "pointer",
                fontSize: "14px",
                lineHeight: "24px",
              }}
            >
              ×
            </button>
          </div>
        )}
      </div>

      {/* 조리방법 섹션 */}
      <div className="mt12">
        <h4 style={{ margin: "8px 0", fontSize: "14px", fontWeight: 600 }}>
          조리방법
        </h4>
        {steps.map((step, index) => (
          <div
            key={index}
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "6px",
              padding: "10px",
              marginBottom: "8px",
              border: "1px solid #e0e0e0",
              borderRadius: "6px",
              background: "#fafafa",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontWeight: 500, minWidth: "50px" }}>
                {index + 1}단계
              </span>
              {steps.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeStep(index)}
                  style={{
                    marginLeft: "auto",
                    padding: "2px 8px",
                    fontSize: "12px",
                    background: "#ff6b6b",
                    color: "#fff",
                    border: "none",
                    borderRadius: "4px",
                    cursor: "pointer",
                  }}
                >
                  삭제
                </button>
              )}
            </div>

            <textarea
              className="input"
              placeholder="조리 방법을 입력하세요"
              value={step.description}
              onChange={(e) => updateStepDescription(index, e.target.value)}
              style={{ minHeight: "60px", resize: "vertical" }}
            />

            {/* 단계 이미지 업로드 */}
            <div>
              <label style={{ fontSize: "12px", color: "#666" }}>
                과정 이미지 (선택)
              </label>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => handleStepImageChange(index, e)}
                style={{ fontSize: "12px", marginTop: "4px" }}
              />
              {step.imagePreview && (
                <div style={{ marginTop: "6px", position: "relative", display: "inline-block" }}>
                  <img
                    src={step.imagePreview}
                    alt={`${index + 1}단계 이미지`}
                    style={{
                      maxWidth: "120px",
                      maxHeight: "120px",
                      borderRadius: "6px",
                      border: "1px solid #ddd",
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => removeStepImage(index)}
                    style={{
                      position: "absolute",
                      top: "-6px",
                      right: "-6px",
                      width: "20px",
                      height: "20px",
                      borderRadius: "50%",
                      background: "#ff6b6b",
                      color: "#fff",
                      border: "none",
                      cursor: "pointer",
                      fontSize: "12px",
                      lineHeight: "20px",
                    }}
                  >
                    ×
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}

        <button
          type="button"
          onClick={addStep}
          style={{
            padding: "6px 12px",
            fontSize: "13px",
            background: "#4dabf7",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
          }}
        >
          + 단계 추가
        </button>
      </div>

      <div className="row mt12 align-center">
        <input
          type="checkbox"
          id="isPublic"
          checked={isPublic}
          onChange={(e) => setIsPublic(e.target.checked)}
        />
        <label htmlFor="isPublic" className="label">
          공개 레시피
        </label>
      </div>

      <button
        className="btn primary mt12"
        onClick={submit}
        disabled={loading}
      >
        {loading ? "등록 중..." : "등록"}
      </button>
    </div>
  );
}

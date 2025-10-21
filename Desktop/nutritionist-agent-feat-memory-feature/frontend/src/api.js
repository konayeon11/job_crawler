// src/api.js
const Api = (() => {
  const base = () => (window.APP_CONFIG?.BACKEND_BASE_URL ?? "");

  async function health() {
    try {
      const res = await fetch(base() + "/health", { cache: "no-store" });
      if (!res.ok) throw new Error(String(res.status));
      return await res.json().catch(() => ({ ok: true }));
    } catch (e) {
      return { ok: false, error: e.message };
    }
  }

  async function analyze({ imageFile, promptText, goals }) {
    if (!imageFile) throw new Error("이미지 파일이 필요합니다.");
    const constraints = {
      prompt: promptText || "레시피 추천",
      max_time: goals?.time ?? null,
      max_sodium: goals?.sodium ?? null,
    };
    const fd = new FormData();
    fd.append("file", imageFile);
    fd.append("constraints", JSON.stringify(constraints));

    const res = await fetch(base() + "/analyze-and-suggest", {
      method: "POST",
      body: fd,
    });
    const ct = res.headers.get("content-type") || "";
    const text = await res.text();
    let data = null;
    try { data = ct.includes("application/json") ? JSON.parse(text) : { raw: text }; } catch {}
    if (!res.ok) {
      let msg = "요청 실패";
      if (res.status === 422) msg = "검증 실패(422): 필드 형식 또는 누락 확인";
      if (res.status === 500) msg = "서버 오류(500): 백엔드 로그 확인 필요";
      throw { status: res.status, message: msg, details: data || text };
    }
    return data ?? {};
  }

  // ✅ 퀘스트 완료 저장 (DB에 XP 적립)
  async function completeQuest({ quest, userId }) {
    const res = await fetch(base() + "/quests/complete", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(userId ? { "X-User-Id": userId } : {}),
      },
      body: JSON.stringify({
        quest_id: quest.id,
        title: quest.title,
        xp: quest.xp,
        reason: quest.reason || "",
        payload: { checks: quest.checks || [] },
      }),
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`퀘스트 저장 실패 (${res.status}) ${t}`);
    }
    return await res.json();
  }

  // (옵션) 프로필 조회
  async function readProfile(userId) {
    const res = await fetch(base() + "/profile", {
      headers: { ...(userId ? { "X-User-Id": userId } : {}) },
    });
    if (!res.ok) throw new Error("프로필 조회 실패");
    return await res.json();
  }

  // ★ 이 반환 객체에 completeQuest가 반드시 포함되어야 합니다.
  return { health, analyze, completeQuest, readProfile };
})();
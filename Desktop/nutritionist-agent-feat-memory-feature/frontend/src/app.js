// frontend.zip/src/app.js (수정됨: 멀티 뷰 구조 반영)
const { createApp, ref, reactive, computed, onMounted } = Vue;

// Font Awesome 아이콘 코드를 가정합니다.
// 실제 환경에서는 Font Awesome 라이브러리 추가가 필요합니다.
const ICONS = {
    main: '🏠', // Home
    inventory: '🍎', // Fridge/Inventory
    chatbot: '💬', // Chat
    profile: '👤', // Profile
    recipe: '🍳' // Recipe
};

createApp({
  setup() {
    // === 상태 관리 ===
    const currentView = ref('main');        // 'main', 'inventory', 'chatbot', 'recipeDetail'
    const imageFile = ref(null);
    const previewURL = ref("");
    const promptText = ref("");
    const goals = reactive({ time: 20, sodium: 1500 }); // 현재 목표

    const running = ref(false);
    const level = ref(1), xp = ref(0), xpNext = ref(100);
    const xpPct = computed(() => Math.round(100 * xp.value / xpNext.value));

    const logs = ref([]);
    const results = ref(null);
    const quests = ref([]);                 // LLM 기반 퀘스트
    const completed = ref(new Set());       // 완료한 퀘스트 id 집합(중복 방지)
    const userId = ref(localStorage.getItem("userId") || "local");
    const health = ref({ ok: null, text: "확인 중..." });
    const selectedRecipe = ref(null);       // ★ 선택된 레시피 (상세 뷰)
    
    // ★ UX 개선 반영: 사용자 프로필 (가정)
    const userProfile = reactive({
        goal: "체중 관리",
        diet: "일반식",
        age: 30
    });


    // === 유틸리티 및 로직 ===
    function navigate(view) {
        currentView.value = view;
        selectedRecipe.value = null; // 뷰 전환 시 상세 레시피 닫기
        window.scrollTo(0, 0); // 스크롤 맨 위로 이동
    }

    function addMsg(html, who = "system") {
      logs.value.push({ who, html });
      setTimeout(() => {
        const el = document.querySelector(".log");
        if (el) el.scrollTop = el.scrollHeight;
      }, 0);
    }
    function gainXP(n) {
      xp.value += n;
      while (xp.value >= xpNext.value) {
        level.value += 1;
        xp.value -= xpNext.value;
        xpNext.value = Math.round(xpNext.value * 1.25);
        addMsg(`🎉 레벨 업! Lv.${level.value} 달성`, "system");
      }
    }
    function onFileChange(e) {
      const f = e.target.files?.[0];
      if (!f) return;
      imageFile.value = f;
      previewURL.value = URL.createObjectURL(f);
      selectedRecipe.value = null; 
      navigate('main'); // 파일 업로드 시 메인으로 이동
    }
    async function doHealth() {
      const h = await Api.health();
      health.value.ok = !!h && h.ok !== false;
      health.value.text = health.value.ok ? "연결 정상" : "연결 확인 필요(/health 없음 가능)";
    }
    function daysLeft(dateStr) {
      const d = new Date(dateStr + "T00:00:00");
      const now = new Date(); const diff = Math.ceil((d - now) / 86400000);
      return diff;
    }
    function dday(dateStr) {
      const left = daysLeft(dateStr);
      return (left >= 0 ? "+" : "") + left;
    }

    // AI 호출
    async function runOnce() {
      if (running.value) return;
      if (!imageFile.value) {
        addMsg("이미지를 업로드해 주세요.", "system"); return;
      }
      running.value = true; 
      results.value = null; 
      logs.value = []; 
      quests.value = [];
      selectedRecipe.value = null;

      addMsg("📤 이미지를 업로드하고 에이전트를 호출합니다...", "system");

      try {
        // [UX 개선] 사용자 프로필 정보도 constraints에 포함한다고 가정
        const constraints = { 
            ...goals, 
            prompt: promptText.value || "레시피 추천",
            user_profile: userProfile 
        };
        const data = await Api.analyze({ imageFile: imageFile.value, constraints });

        if (data?.logs) data.logs.forEach(line => addMsg(line, "system"));
        if (data?.message) addMsg(String(data.message), "system");

        results.value = data;
        quests.value = Array.isArray(data.quests) ? data.quests : [];

        addMsg("✅ 완료. 레시피/퀘스트/인벤토리를 표시합니다.", "system");
      } catch (err) {
        let msg = err?.message || "요청 실패";
        addMsg(`❌ ${msg}\n\n세부정보:\n${typeof err?.details === "string" ? err.details : JSON.stringify(err?.details, null, 2)}`, "system");
      } finally {
        running.value = false;
      }
    }

    // 퀘스트 완료
    async function complete(q) {
      if (completed.value.has(q.id)) return;
      // ... (기존 complete 로직 유지)
      try {
        const r = await Api.completeQuest({ quest: q, userId: userId.value });
        completed.value.add(q.id);
        gainXP(q.xp);
        addMsg(`✅ '${q.title}' 완료! +${q.xp}XP`, "system");
      } catch (e) {
        addMsg(`❌ 퀘스트 저장 실패: ${e.message}`, "system");
      }
    }

    // 레시피 선택 (상세 보기)
    function selectRecipe(r){
      selectedRecipe.value = r;
      currentView.value = 'recipeDetail'; // ★ 뷰 전환
      addMsg(`🍳 레시피 상세 보기: ${r.name || r.title || "선택됨"}`, "system");
      window.scrollTo(0, 0); 
    }
    
    // 상세 레시피 뷰 닫기
    function closeRecipeDetail() {
        selectedRecipe.value = null;
        currentView.value = 'main'; // ★ 메인 뷰로 돌아감
    }

    onMounted(() => { doHealth().catch(() => {}); });

    // === 반환 상태 및 함수 ===
    return {
      currentView, navigate, // ★ 뷰 상태 및 네비게이션
      imageFile, previewURL, promptText, goals, userProfile, // ★ userProfile 추가
      running, level, xp, xpNext, xpPct, logs, results, quests,
      completed, userId, selectedRecipe,
      onFileChange, runOnce, complete, selectRecipe, closeRecipeDetail,
      health, daysLeft, dday, ICONS
    };
  },

  template: `
  <div class="app">
    <div class="topbar" v-if="currentView !== 'recipeDetail'">
        <div class="app-title">
          <div class="logo"></div>
          <div class="title-col">
            <b>AI 영양사</b>
            <span class="small">{{ health.text }}</span>
          </div>
        </div>
        <div class="hud">
            <button @click="navigate('profile')" class="pill" style="min-height: auto; padding: 4px 8px; font-weight: normal; background: var(--card); border: 1px solid var(--border-color);">
                {{ ICONS.profile }} {{ userProfile.goal }}
            </button>
            <div class="xpbar"><i :style="{width: xpPct + '%'}"></i></div>
        </div>
    </div>

    <div class="content">

        <template v-if="currentView === 'main'">

            <section class="panel">
              <div class="ph">냉장고 사진 스캔하기</div>
              <div class="section upload">
                <div class="filebox">
                  <input type="file" accept="image/*" @change="onFileChange" />
                </div>
                <div v-if="previewURL" class="preview">
                  <img :src="previewURL" alt="preview"/>
                  <div class="small">스캔할 사진 미리보기</div>
                </div>

                <input type="text" v-model="promptText" placeholder="예) 20분 내 단백질 위주 레시피" />

                <div class="grid2">
                  <div class="input-like row" style="padding:0">
                    <input type="number" min="5" max="60" step="5" v-model.number="goals.time" placeholder="최대 시간(분)" style="padding:12px; border:none; border-radius:10px 0 0 10px;" />
                    <span style="padding-right:12px; color:var(--accent2); font-weight:700;">분</span>
                  </div>
                  <div class="input-like row" style="padding:0">
                    <input type="number" min="500" max="3000" step="100" v-model.number="goals.sodium" placeholder="최대 나트륨(mg)" style="padding:12px; border:none; border-radius:10px 0 0 10px;" />
                    <span style="padding-right:12px; color:var(--accent2); font-weight:700;">mg</span>
                  </div>
                </div>

                <div class="btn-row">
                  <button @click="runOnce" :disabled="running">{{ running ? "⏳ 분석 중..." : "🍳 레시피/퀘스트 추천받기" }}</button>
                </div>
              </div>
            </section>
            
            <section v-if="results?.recipes?.length" class="panel">
              <div class="ph">✨ 오늘의 추천 레시피 ({{ results.recipes.length }}개)</div>
              <div class="section" style="display:flex;flex-direction:column;gap:10px">
                <div v-for="(r, idx) in results.recipes.slice(0,3)" :key="r.id || idx" 
                     class="recipe-card" @click="selectRecipe(r)"
                     :style="{borderColor: selectedRecipe?.id === r.id ? 'var(--good)' : 'var(--border-color)'}">
                  <div class="rc-title">
                    <b>{{ r.name || r.title || \`레시피 \${idx+1}\` }}</b>
                    <span class="qr-title xp" v-if="r.xp">+{{ r.xp }}XP</span>
                  </div>
                  <div class="small" v-if="r.description">{{ r.description }}</div>
                  <ul class="rc-meta">
                    <li v-if="r.time"><strong>예상 시간:</strong> {{ r.time || r.estimated_time || r.total_time || '정보 없음' }}</li>
                    <li v-if="r.calories || r.protein">
                        <span style="background:var(--card); padding:2px 6px; border-radius:4px; font-size:11px; margin-right:5px;" v-if="r.calories">🔥 {{ r.calories }} Kcal</span>
                        <span style="background:var(--card); padding:2px 6px; border-radius:4px; font-size:11px;" v-if="r.protein">💪 {{ r.protein }}g 단백질</span>
                    </li>
                  </ul>
                  <div style="margin-top:8px">
                    <button @click.stop="selectRecipe(r)" style="background:var(--accent2)">
                      레시피 상세 보기
                    </button>
                  </div>
                </div>
              </div>
            </section>

            <section v-if="quests.length" class="panel">
              <div class="ph">🎯 일일 퀘스트 ({{ quests.length }}개)</div>
              <div class="section" style="display:flex;flex-direction:column;gap:10px">
                <div v-for="q in quests" :key="q.id" class="quest-row">
                  <div class="qr-title">
                    <b>{{ q.title }}</b>
                    <span class="xp">+{{ q.xp }}XP</span>
                  </div>
                  <div class="qr-reason small">{{ q.reason }}</div>
                  <div style="display:flex;gap:8px;margin-top:8px">
                    <button @click="complete(q)" :disabled="completed.has(q.id)">
                      {{ completed.has(q.id) ? "✅ 완료됨" : "퀘스트 완료하기" }}
                    </button>
                  </div>
                </div>
              </div>
            </section>
            
            <section class="panel">
                <div class="ph">실행 로그</div>
                <div class="section">
                    <div class="log">
                        <div v-for="(m,i) in logs" :key="i" class="msg">
                            <div class="avatar-b" :style="{background: m.who === 'me' ? 'var(--good)' : 'var(--accent)'}"></div>
                            <div class="bubble" v-html="m.html"></div>
                        </div>
                    </div>
                </div>
            </section>
            
            <section v-if="results" class="panel">
                <div class="ph">추천 결과 (Raw)</div>
                <div class="section">
                    <pre class="small" style="white-space:pre-wrap">{{ JSON.stringify(results, null, 2) }}</pre>
                </div>
            </section>

        </template>
        
        <template v-else-if="currentView === 'inventory'">
            <section class="panel">
              <div class="ph">냉장고 인벤토리 관리</div>
              <div class="section">
                <p v-if="!results?.inventory" class="small" style="text-align: center;">
                    메인 페이지에서 냉장고 사진을 스캔해야 재료 목록이 표시됩니다.
                </p>
                <div v-else class="inv-grid">
                  <div v-for="(it,name) in results.inventory" :key="name"
                       class="inv-card"
                       :class="{'expiring': daysLeft(it.expiry_date) <= 3 && daysLeft(it.expiry_date) >= 0,
                                'expired': daysLeft(it.expiry_date) < 0}">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                      <b>{{ name }}</b>
                      <span class="badge">수량: {{ it.quantity }}</span>
                    </div>
                    <div class="small">D{{ dday(it.expiry_date) }} · 유통기한 {{ it.expiry_date }}</div>
                  </div>
                </div>
              </div>
            </section>
        </template>
        
        <template v-else-if="currentView === 'chatbot'">
            <section class="panel" style="text-align: center;">
              <div class="ph">AI 에이전트와 대화하기</div>
              <div class="section">
                <div style="padding: 50px 0;">
                    <div class="nav-icon" style="font-size: 50px; color: var(--accent);">{{ ICONS.chatbot }}</div>
                    <p style="font-size: 16px; margin-top: 15px;">
                      AI 에이전트 챗봇 기능은 현재 개발 중입니다.<br>
                      잠시만 기다려주세요!
                    </p>
                </div>
              </div>
            </section>
        </template>
        
        <template v-else-if="currentView === 'profile'">
            <section class="panel">
              <div class="ph">내 프로필 및 목표 설정</div>
              <div class="section">
                <p style="margin-bottom: 20px;">
                    영양 및 레시피 추천의 정확도를 높이기 위해 필요한 정보입니다.
                </p>
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <input type="text" v-model="userProfile.goal" placeholder="건강 목표 (예: 체중 감량)" />
                    <input type="text" v-model="userProfile.diet" placeholder="식단 유형 (예: 일반식, 채식)" />
                    <input type="number" v-model.number="userProfile.age" placeholder="나이" />
                    <button style="background: var(--good); margin-top: 10px;">정보 저장 (백엔드 연동 필요)</button>
                </div>
              </div>
            </section>
        </template>

    </div>

    <div v-if="selectedRecipe" class="recipe-detail-view">
        <button @click="closeRecipeDetail" style="margin-bottom: 20px; width: auto; background: var(--accent2); box-shadow: none;">
            ← 메인 화면으로 돌아가기
        </button>

        <h2>{{ selectedRecipe.name || selectedRecipe.title || '레시피 상세' }}</h2>
        <div class="detail-meta">
            <span v-if="selectedRecipe.xp" style="border-color:var(--good); color:var(--good); background:#e6ffed">경험치: +{{ selectedRecipe.xp }}XP</span>
            <span v-if="selectedRecipe.time">예상 시간: {{ selectedRecipe.time || selectedRecipe.estimated_time || selectedRecipe.total_time }}</span>
            <span v-if="selectedRecipe.calories">칼로리: {{ selectedRecipe.calories }}Kcal</span>
            <span v-if="selectedRecipe.sodium">나트륨: {{ selectedRecipe.sodium }}mg</span>
            <span v-if="selectedRecipe.protein">단백질: {{ selectedRecipe.protein }}g</span>
        </div>
        
        <p v-if="selectedRecipe.description">{{ selectedRecipe.description }}</p>

        <h3 v-if="selectedRecipe.ingredients?.length">필요 재료</h3>
        <ul v-if="selectedRecipe.ingredients?.length">
            <li v-for="(ing, i) in selectedRecipe.ingredients" :key="'ing'+i">{{ ing }}</li>
        </ul>

        <h3 v-if="selectedRecipe.steps?.length">조리 순서</h3>
        <ol v-if="selectedRecipe.steps?.length">
            <li v-for="(step, i) in selectedRecipe.steps" :key="'step'+i">{{ step }}</li>
        </ol>

        <h3 v-if="selectedRecipe.tip">AI 팁</h3>
        <p v-if="selectedRecipe.tip" style="background:var(--card); padding:15px; border-radius:10px; color:var(--text)">{{ selectedRecipe.tip }}</p>
    </div>

    <div class="bottom-nav" v-if="currentView !== 'recipeDetail'">
        <div class="nav-item" :class="{active: currentView === 'main'}" @click="navigate('main')">
            <div class="nav-icon">{{ ICONS.main }}</div>
            <span>레시피 추천</span>
        </div>
        <div class="nav-item" :class="{active: currentView === 'inventory'}" @click="navigate('inventory')">
            <div class="nav-icon">{{ ICONS.inventory }}</div>
            <span>냉장고 재료</span>
        </div>
        <div class="nav-item" :class="{active: currentView === 'chatbot'}" @click="navigate('chatbot')">
            <div class="nav-icon">{{ ICONS.chatbot }}</div>
            <span>AI 챗봇</span>
        </div>
        <div class="nav-item" :class="{active: currentView === 'profile'}" @click="navigate('profile')">
            <div class="nav-icon">{{ ICONS.profile }}</div>
            <span>마이 프로필</span>
        </div>
    </div>
  </div>
  `
}).mount("#app");
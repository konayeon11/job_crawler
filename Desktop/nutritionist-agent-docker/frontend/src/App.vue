<template>
  <!-- 레시피 상세 뷰 -->
  <div v-if="isRecipeDetailVisible && selectedRecipe" class="recipe-detail-container">
    <div class="recipe-detail-header">
      <button @click="closeRecipeDetail" class="back-button">← 뒤로</button>
      <h2 class="recipe-detail-title">{{ selectedRecipe.title }}</h2>
    </div>
    <div class="recipe-detail-content">
      <div class="detail-section">
        <p><strong>난이도:</strong> {{ selectedRecipe.difficulty || '정보 없음' }}</p>
        <p><strong>소요 시간:</strong> {{ selectedRecipe.time_minutes ? selectedRecipe.time_minutes + '분' : '정보 없음' }}</p>
        <p v-if="selectedRecipe.time_breakdown"> (준비: {{ selectedRecipe.time_breakdown.prep || 0 }}분, 요리: {{ selectedRecipe.time_breakdown.cook || 0 }}분)</p>
        <p><strong>제공량:</strong> {{ selectedRecipe.servings || '정보 없음' }}</p>
        <p v-if="selectedRecipe.tags && selectedRecipe.tags.length > 0"><strong>태그:</strong> {{ selectedRecipe.tags.join(', ') }}</p>
      </div>

      <div class="detail-section">
        <h3>재료</h3>
        <ul class="ingredient-list">
          <li v-for="(item, index) in selectedRecipe.ingredients" :key="index">{{ item }}</li>
        </ul>
      </div>

      <div class="detail-section">
        <h3>조리법</h3>
        <ol class="step-list">
          <li v-for="(step, i) in selectedRecipe.steps" :key="i">{{ step }}</li>
        </ol>
      </div>

      <div v-if="selectedRecipe.nutrition" class="detail-section">
        <h3>영양 정보 (1인분)</h3>
        <p>
          <strong>칼로리:</strong> {{ selectedRecipe.nutrition.calories_kcal || 'N/A' }}kcal | 
          <strong>단백질:</strong> {{ selectedRecipe.nutrition.protein_g || 'N/A' }}g | 
          <strong>탄수화물:</strong> {{ selectedRecipe.nutrition.carbs_g || 'N/A' }}g | 
          <strong>지방:</strong> {{ selectedRecipe.nutrition.fat_g || 'N/A' }}g | 
          <strong>나트륨:</strong> {{ selectedRecipe.nutrition.sodium_mg || 'N/A' }}mg
        </p>
      </div>

      <div v-if="selectedRecipe.source && selectedRecipe.source.url" class="detail-section source-section">
        <a :href="selectedRecipe.source.url" target="_blank" class="source-link">레시피 출처 보기</a>
      </div>
    </div>
  </div>

  <!-- 채팅 뷰 -->
  <div v-show="!isRecipeDetailVisible" class="chat-container">
    <div class="message-area" ref="messageArea">
      <div v-for="(message, index) in messages" :key="index" class="message-wrapper" :class="message.sender">
        <div class="message-bubble">
          <img v-if="message.image" :src="message.image" alt="Uploaded content" class="uploaded-image" />
          <p v-else v-html="formatMessage(message.text)"></p>
        </div>
      </div>
      <div v-if="isLoading" class="message-wrapper assistant">
        <div class="message-bubble loading-bubble"><div class="dot-flashing"></div></div>
      </div>
    </div>
    <form @submit.prevent="sendMessage" class="input-area">
      <label for="file-upload" class="file-upload-label">📎</label>
      <input id="file-upload" type="file" @change="handleFileUpload" accept="image/*" />
      <input type="text" v-model="newMessage" :placeholder="selectedFile ? selectedFile.name : '재료를 입력하거나 사진을 첨부하세요...'" :disabled="isLoading" />
      <button type="submit" :disabled="isLoading || (!selectedFile && !newMessage.trim())">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="currentColor" d="M3 20V4a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v16l-4-4H5a2 2 0 0 1-2-2Z"/></svg>
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue';

const messages = ref([
  { sender: 'assistant', text: '안녕하세요! AI 영양사입니다. 재료를 입력하시거나 📎 버튼으로 냉장고 사진을 보내주세요.' }
]);
const newMessage = ref('');
const isLoading = ref(false);
const messageArea = ref(null);
const selectedFile = ref(null);
const isRecipeDetailVisible = ref(false);
const selectedRecipe = ref(null);
const latestRecipes = ref([]); // 최신 레시피 목록 저장

// 컴포넌트 마운트 시 이벤트 리스너 설정
onMounted(() => {
  if (messageArea.value) {
    messageArea.value.addEventListener('click', (event) => {
      const button = event.target.closest('.recipe-title-button');
      if (button && button.dataset.recipeIndex) {
        const index = parseInt(button.dataset.recipeIndex);
        if (latestRecipes.value[index]) {
          displayDetailedRecipe(latestRecipes.value[index]);
        }
      }
    });
  }
});

const handleFileUpload = (event) => {
  const file = event.target.files[0];
  if (file) {
    selectedFile.value = file;
    newMessage.value = '';
  }
};

const sendMessage = async () => {
  const hasFile = selectedFile.value;
  const hasText = newMessage.value.trim();
  if ((!hasFile && !hasText) || isLoading.value) return;

  isLoading.value = true;
  
  if (hasFile) {
    const file = selectedFile.value;
    const imageUrl = URL.createObjectURL(file);
    messages.value.push({ sender: 'user', image: imageUrl });
    selectedFile.value = null;
    scrollToBottom();
    await handleImageQuery(file);
  } else if (hasText) {
    const userMessage = newMessage.value.trim();
    messages.value.push({ sender: 'user', text: userMessage });
    newMessage.value = '';
    scrollToBottom();
    await handleTextQuery(userMessage);
  }
};

const handleImageQuery = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('constraints', JSON.stringify({})); 

  try {
    const response = await fetch('http://127.0.0.1:8000/analyze-and-suggest', {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error(`서버 오류: ${response.status}`);
    const result = await response.json();
    displayAnalysisResult(result);
  } catch (error) {
    handleApiError(error);
  }
};

const handleTextQuery = async (textMessage) => {
  try {
    const response = await fetch('http://127.0.0.1:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: textMessage }),
    });
    if (!response.ok) throw new Error(`서버 오류: ${response.status}`);
    const result = await response.json();
    displayChatResult(result);
  } catch (error) {
    handleApiError(error);
  }
};

const displayAnalysisResult = (result) => {
  let assistantResponse = '분석이 완료되었습니다!<br><br>';
  if (result.inventory) {
    const ingredients = Object.keys(result.inventory);
    assistantResponse += `<b>[인식된 재료]</b><br>${ingredients.join(', ')}<br><br>`;
  }
  if (result.recipes && result.recipes.length > 0) {
    latestRecipes.value = result.recipes; // 레시피 목록 저장
    assistantResponse += '<b>[추천 레시피]</b><br>';
    result.recipes.forEach((recipe, i) => {
      assistantResponse += `<button class="recipe-title-button" data-recipe-index="${i}"><b>${i + 1}. ${recipe.title}</b></button><br>`;
      if (recipe.missing && recipe.missing.length > 0) {
        assistantResponse += `<i>- 추가 필요: ${recipe.missing.join(', ')}</i><br><br>`;
      } else {
        assistantResponse += `<i>- 추가 재료 없음!</i><br><br>`;
      }
    });
  } else {
    assistantResponse += '아쉽지만 추천할 만한 레시피를 찾지 못했어요.';
  }

  if (result.shopping_list && result.shopping_list.items && result.shopping_list.items.length > 0) {
    assistantResponse += '<br><b>[부족한 재료 구매하기]</b><br>';
    result.shopping_list.items.forEach(item => {
      assistantResponse += `- <a href="${item.url}" target="_blank">${item.name} (${item.quantity})</a><br>`;
    });
  }

  messages.value.push({ sender: 'assistant', text: assistantResponse });
  finalizeMessage();
};

const displayChatResult = (result) => {
  let assistantResponse = result.response || '응답을 받을 수 없습니다.';

  if (result.recipes && result.recipes.length > 0) {
    latestRecipes.value = result.recipes;
    assistantResponse += '<br><br><b>[추천 레시피]</b><br>';
    result.recipes.forEach((recipe, i) => {
      assistantResponse += `<button class="recipe-title-button" data-recipe-index="${i}"><b>${i + 1}. ${recipe.title}</b></button><br>`;
      if (recipe.missing && recipe.missing.length > 0) {
        assistantResponse += `<i>- 추가 필요: ${recipe.missing.join(', ')}</i><br><br>`;
      } else {
        assistantResponse += `<i>- 추가 재료 없음!</i><br><br>`;
      }
    });
  }

  if (result.shopping_list && result.shopping_list.items && result.shopping_list.items.length > 0) {
    assistantResponse += '<br><br><b>[쇼핑 리스트]</b><br>';
    result.shopping_list.items.forEach(item => {
      assistantResponse += `- <a href="${item.url}" target="_blank">${item.name} (${item.quantity})</a><br>`;
    });
  }
  messages.value.push({ sender: 'assistant', text: assistantResponse });
  finalizeMessage();
};

const displayDetailedRecipe = (recipe) => {
  selectedRecipe.value = recipe;
  isRecipeDetailVisible.value = true;
};

const closeRecipeDetail = () => {
  isRecipeDetailVisible.value = false;
  selectedRecipe.value = null;
};

const handleApiError = (error) => {
  console.error('API 요청 실패:', error);
  messages.value.push({ sender: 'assistant', text: '죄송합니다, 서버와 통신 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.' });
  finalizeMessage();
};

const finalizeMessage = () => {
  isLoading.value = false;
  scrollToBottom();
};

const formatMessage = (text) => {
  // v-html을 사용하므로, 버튼 클래스를 유지하도록 수정
  return text.replace(/\n/g, '<br>');
};

const scrollToBottom = () => {
  nextTick(() => {
    if (messageArea.value) {
      messageArea.value.scrollTop = messageArea.value.scrollHeight;
    }
  });
};
</script>

<style scoped>
:root {
  --primary-color: #4A90E2;
  --background-color: #FDFDFD;
  --container-bg: #ffffff;
  --text-dark: #555555;
  --text-light: #ffffff;
  --border-color: #EEEEEE;
}

.chat-container, .recipe-detail-container {
  display: flex;
  flex-direction: column;
  height: 80vh;
  width: 400px;
  max-width: 100%;
  margin: 2rem auto;
  background-color: var(--container-bg);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  border: 1px solid var(--border-color);
}

/* Recipe Detail View */
.recipe-detail-header {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-color);
  background-color: #fdfdfd;
  position: sticky;
  top: 0;
  z-index: 10;
}

.back-button {
  background: none;
  border: none;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  color: var(--primary-color);
  padding: 8px 0;
  margin-right: 15px;
}

.recipe-detail-title {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--text-dark);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recipe-detail-content {
  padding: 20px;
  overflow-y: auto;
  line-height: 1.7;
}

.detail-section {
  margin-bottom: 24px;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 20px;
}
.detail-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.detail-section h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 12px;
}

.ingredient-list, .step-list {
  padding-left: 20px;
  margin: 0;
}
.ingredient-list li, .step-list li {
  margin-bottom: 8px;
}

.source-section {
  text-align: center;
  margin-top: 20px;
}

.source-link {
  display: inline-block;
  padding: 10px 20px;
  background-color: var(--primary-color);
  color: var(--text-light);
  text-decoration: none;
  border-radius: 25px;
  font-weight: 500;
  transition: background-color 0.3s;
}
.source-link:hover {
  background-color: #357ABD;
}


/* Chat View */
.message-area { flex-grow: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; background-color: var(--background-color); } 
.message-wrapper { display: flex; max-width: 85%; } 
.message-wrapper.user { align-self: flex-end; } 
.message-wrapper.assistant { align-self: flex-start; } 
.message-bubble { padding: 12px 18px; border-radius: 20px; color: var(--text-dark); line-height: 1.6; word-wrap: break-word; box-shadow: 0 2px 4px rgba(0,0,0,0.05); } 
.message-wrapper.user .message-bubble { background-color: var(--primary-color); color: var(--text-light); border-top-right-radius: 4px; } 
.message-wrapper.assistant .message-bubble { background-color: #e9e9eb; color: var(--text-dark); border-top-left-radius: 4px; } 
.message-bubble p { margin: 0; } 
.uploaded-image { max-width: 100%; border-radius: 15px; margin-top: 5px; } 
.input-area { display: flex; align-items: center; padding: 12px; border-top: 1px solid var(--border-color); background-color: var(--container-bg); } 
.file-upload-label { cursor: pointer; padding: 10px; font-size: 24px; color: #555; transition: color 0.2s; } 
.file-upload-label:hover { color: var(--primary-color); } 
input[type="file"] { display: none; } 
.input-area input[type="text"] { flex-grow: 1; border: none; padding: 12px; border-radius: 20px; background-color: #f0f0f0; outline: none; font-size: 16px; margin: 0 8px; } 
.input-area input[type="text"]:focus { background-color: #e9e9e9; } 
.input-area button { background: none; border: none; padding: 8px; cursor: pointer; color: var(--primary-color); } 
.input-area button:disabled { color: #a0a0a0; cursor: not-allowed; } 
.input-area button svg { width: 24px; height: 24px; } 
.loading-bubble { padding: 18px; } 
.dot-flashing { position: relative; width: 10px; height: 10px; border-radius: 5px; background-color: #999; color: #999; animation: dot-flashing 1s infinite linear alternate; animation-delay: .5s; } 
.dot-flashing::before, .dot-flashing::after { content: ''; display: inline-block; position: absolute; top: 0; } 
.dot-flashing::before { left: -15px; width: 10px; height: 10px; border-radius: 5px; background-color: #999; color: #999; animation: dot-flashing 1s infinite alternate; animation-delay: 0s; } 
.dot-flashing::after { left: 15px; width: 10px; height: 10px; border-radius: 5px; background-color: #999; color: #999; animation: dot-flashing 1s infinite alternate; animation-delay: 1s; } 
 @keyframes dot-flashing { 0% { background-color: #999; } 50%, 100% { background-color: #ccc; } } 

/* Style for recipe buttons in chat */
:deep(.recipe-title-button) {
  background: none;
  border: none;
  padding: 0;
  margin: 4px 0;
  text-align: left;
  font-size: inherit;
  font-family: inherit;
  color: var(--primary-color);
  cursor: pointer;
  text-decoration: underline;
}
:deep(.recipe-title-button:hover) {
  color: #357ABD;
}
</style>
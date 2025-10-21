// Same-origin 기본. 다른 포트/도메인 사용 시 index.html에서 window.BACKEND_BASE_URL를 주입하세요.
window.APP_CONFIG = {
  BACKEND_BASE_URL: window.BACKEND_BASE_URL || ""
};

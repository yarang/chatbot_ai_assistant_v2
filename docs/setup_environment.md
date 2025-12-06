# 환경 변수 설정 가이드

이 프로젝트를 실행하기 위해 필요한 API Key들을 발급받고 `.env` 파일에 설정하는 방법입니다.

## 1. Google Gemini API 설정

Google의 Generative AI 모델을 사용하기 위해 필요합니다.

1.  [Google AI Studio](https://aistudio.google.com/)에 접속합니다.
2.  좌측 메뉴에서 "Get API key"를 클릭합니다.
3.  "Create API key" 버튼을 눌러 새 키를 생성합니다.
4.  생성된 키를 `GEMINI_API_KEY`에 입력합니다.

## 2. Telegram Bot 설정

텔레그램 봇을 생성하고 연동하기 위해 필요합니다.

1.  텔레그램 앱에서 [@BotFather](https://t.me/BotFather)를 검색합니다.
2.  `/newbot` 명령어를 입력하여 새로운 봇을 생성합니다.
3.  봇의 이름과 유저네임을 설정하면 **Access Token**이 발급됩니다.
4.  이 토큰을 `TELEGRAM_BOT_TOKEN`에 입력합니다.

### 2.1 로컬 웹훅 설정 (Ngrok)

텔레그램은 HTTPS URL로만 웹훅을 보낼 수 있습니다. 로컬 개발 환경에서는 [ngrok](https://ngrok.com/)을 사용하여 로컬 포트를 외부로 노출해야 합니다.

1.  **Ngrok 설치 및 실행**:
    ```bash
    # 포트 8000번을 외부로 노출
    ngrok http 8000
    ```
2.  **URL 복사**:
    `Forwarding` 항목에 있는 `https://...ngrok-free.app` 형태의 주소를 복사합니다.
3.  **환경 변수 설정**:
    `.env` 파일의 `TELEGRAM_WEBHOOK_URL`에 복사한 주소 뒤에 `/telegram/webhook` 경로를 붙여 입력합니다.
    예: `TELEGRAM_WEBHOOK_URL=https://1234.ngrok-free.app/telegram/webhook`

## 3. Tavily Search API 설정

AI가 웹 검색을 통해 최신 정보를 얻기 위해 사용됩니다.

1.  [Tavily](https://tavily.com/) 웹사이트에 접속하여 회원가입합니다.
2.  대시보드에서 API Key를 복사합니다.
3.  복사한 키를 `TAVILY_API_KEY`에 입력합니다.

## 4. Notion API 설정

Notion 페이지를 검색, 생성, 수정하기 위해 필요합니다.

### 4.1 Integration 생성 (API Key)
1.  [My Integrations](https://www.notion.so/my-integrations) 페이지로 이동합니다.
2.  "새 API 통합 만들기"를 클릭합니다.
3.  이름(예: `My Chatbot`)을 입력하고 워크스페이스를 선택하여 제출합니다.
4.  "시크릿 토큰 표시"를 눌러 **Internal Integration Secret**을 복사합니다.
5.  이 값을 `NOTION_API_KEY`에 입력합니다.

### 4.2 페이지 연결 및 Database ID 확인
1.  봇이 접근하길 원하는 Notion 페이지나 데이터베이스를 엽니다.
2.  우측 상단 `...` 메뉴 -> `연결(Connect)` -> 위에서 만든 Integration을 선택하여 연결합니다.
3.  브라우저 주소창의 URL에서 **Database ID**를 찾습니다.
    *   URL 형식: `https://www.notion.so/myworkspace/{database_id}?v=...`
    *   `https://www.notion.so/` 뒤의 32자리 문자열이 ID입니다.
4.  이 값을 `NOTION_DATABASE_ID`에 입력합니다.

---

## .env 파일 예시

위에서 얻은 값들을 `.env` 파일에 다음과 같이 작성하세요:

```env
# Google Gemini
GEMINI_API_KEY=your_gemini_api_key_here

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Tavily Search
TAVILY_API_KEY=your_tavily_api_key_here

# Notion
NOTION_API_KEY=your_notion_api_key_here
NOTION_DATABASE_ID=your_notion_database_id_here
```

Antigravity IDE에서 AI에게 코드를 요청하거나, 직접 개발할 때 기준이 될 \*\*「FastAPI + LangGraph + LangChain 아키텍처 개발 매뉴얼」\*\*입니다.

이 내용을 프로젝트의 `README.md`나 `DEV_GUIDE.md`에 포함하거나, Antigravity의 "Custom Instructions(커스텀 지침)" 또는 "System Prompt"에 입력하여 AI가 이 구조대로 코드를 짜도록 유도하십시오.

-----

# 📘 Antigravity 프로젝트 개발 표준 매뉴얼 (v1.0)

## 1\. 아키텍처 개요 (Architecture Overview)

본 프로젝트는 **Layered Architecture (FastAPI + Services + Agent)**를 따릅니다.

  * **Layer 1: Interface (FastAPI)** - 외부 요청 수신 및 응답 반환.
  * **Layer 2: Service (Services)** - 비즈니스 로직 및 Agent 호출/제어.
  * **Layer 3: Agent (LangGraph)** - "AI 오케스트레이션". 작업 흐름(Flow) 및 상태(State) 관리.
  * **Layer 4: Execution (LangChain)** - "AI 작업자(Worker)". LLM 호출, 도구 실행.
  * **Layer 5: Data (Repository)** - 데이터베이스 액세스 (CRUD).

-----

## 2\. 디렉토리 표준 (Directory Standard)

모든 코드는 아래 경로 규칙을 준수해야 합니다.

```plaintext
app/
├── api/
│   └── v1/
│       └── endpoints/    # [L1] API 라우터 (그래프 실행 진입점)
├── schemas/              # [L1] Pydantic DTO (API 요청/응답 정의)
├── services/             # [L2] 비즈니스 로직 (Service Layer)
├── repository/           # [L3] 데이터 액세스 (Repository Layer)
├── models/               # [L3] 데이터베이스 모델 (SQLAlchemy)
├── agent/                # [Agent] LangGraph 오케스트레이션 계층
│   ├── state.py          #      - 그래프 상태(TypedDict) 정의
│   ├── graph.py          #      - 그래프 구성 (Node+Edge 연결) 및 컴파일
│   └── nodes/            #      - 개별 노드 로직 (State 입력 -> State 업데이트)
│       ├── chat_node.py
│       ├── search_node.py
│       ├── notion_node.py #      - Notion 검색/수정 노드
│       └── router_node.py
├── llm/                  # [Worker] LangChain 실행 계층 (순수 로직)
│   ├── chains/           #      - 재사용 가능한 Chain (Runnable)
│   │   ├── chat_chain.py
│   │   ├── search_chain.py
│   │   └── notion_chain.py
│   ├── tools/            #      - 커스텀 도구 (@tool)
│   └── prompts/          #      - 프롬프트 템플릿 파일 관리
└── core/                 # 공통 설정 (Env, Security 등)
    ├── config.py         #      - 환경 변수 설정
    └── notion_client.py  #      - Notion API 클라이언트 Wrapper
```

-----

## 3\. 개발 프로세스 (Step-by-Step Workflow)

기능 개발 시 반드시 다음 순서로 진행합니다.

### Step 1. 스키마 정의 (`schemas/`)

  * API가 받을 입력(Request)과 내보낼 출력(Response)을 정의합니다.

### Step 2. 단위 로직 구현 (`llm/`)

  * **원칙:** 이 계층은 LangGraph(State)를 몰라야 합니다.
  * 순수한 입력(`dict` or `str`)을 받아 결과(`str` or `dict`)를 반환하는 **Chain**이나 **Tool**을 만듭니다.
  * 파일명 규칙: `*_chain.py` (예: `summary_chain.py`)

### Step 3. 상태 정의 (`agent/state.py`)

  * 그래프 전체에서 공유할 메모리 구조(`AgentState`)를 정의합니다.
  * 필수 필드: `messages` (대화 기록), `next_step` (라우팅 제어용).

### Step 4. 노드 래핑 (`agent/nodes/`)

  * Step 2에서 만든 Chain을 호출하여, Step 3의 State를 업데이트하는 함수를 만듭니다.
  * **함수 시그니처:** `def some_node(state: AgentState) -> dict:`
  * 반환값은 전체 State가 아니라 \*\*업데이트할 필드(Diff)\*\*만 반환합니다.

### Step 5. 그래프 조립 (`agent/graph.py`)

  * `StateGraph`를 생성하고 노드와 엣지(조건부 엣지 포함)를 연결합니다.
  * 최종적으로 `.compile()`된 `CompiledGraph` 객체를 반환하는 함수를 작성합니다.

### Step 6. API 노출 (`api/`)

  * FastAPI 라우터에서 그래프의 `.invoke()` 또는 `.stream()` 메서드를 호출합니다.

-----

## 4\. 계층별 코딩 가이드라인 (Coding Guidelines)

### 4.1. LangChain (Worker) 작성 규칙

  * **LCEL 사용:** 가능한 `|` 연산자를 사용한 LCEL(LangChain Expression Language)로 작성합니다.
  * **프롬프트 분리:** 프롬프트가 길어지면 `llm/prompts/` 내의 별도 파일이나 상수로 분리합니다.
  * **의존성 최소화:** 특정 웹 프레임워크나 그래프 로직에 의존하지 않도록 작성합니다.

<!-- end list -->

```python
# [Good] llm/chains/rag_chain.py
def get_rag_chain():
    return prompt | llm | StrOutputParser()
```

### 4.2. LangGraph (Manager) 작성 규칙

  * **State 불변성 유의:** 리스트나 딕셔너리 업데이트 시 기존 데이터를 덮어쓸지, 추가(Append)할지 `Annotated`를 통해 명확히 정의합니다.
  * **조건부 로직:** 분기 처리는 반드시 `add_conditional_edges`를 사용하며, 로직은 별도의 조건 함수(`should_continue` 등)로 분리합니다.

<!-- end list -->

```python
# [Good] agent/nodes/search_node.py
async def search_node(state: AgentState):
    # Chain 호출
    result = await search_chain.ainvoke(...) 
    # State 업데이트 반환
    return {"messages": [result]} 
```

### 4.3. FastAPI (Interface) 작성 규칙

  * **비동기 필수:** LangGraph 실행은 블로킹 작업이 될 수 있으므로 반드시 `async def`를 사용하고 `await graph.ainvoke()`를 호출합니다.

-----

## 5\. Antigravity AI 프롬프팅 지침

Antigravity에서 코드를 생성할 때 서두에 다음 내용을 붙여넣으십시오.

> "이 프로젝트는 FastAPI + LangGraph + LangChain 구조를 따릅니다.
>
> 1.  **LLM 로직**은 `app/llm/chains`에 순수 Chain으로 작성하세요.
> 2.  **그래프 노드**는 `app/agent/nodes`에서 State를 받아 Chain을 호출하고 State 업데이트분을 반환하는 형태로 작성하세요.
> 3.  **그래프 구성**은 `app/agent/graph.py`에서 수행하세요.
> 4.  최종적으로 `app/api`에서 그래프를 호출하세요.
>
> 위 \*\*'개발 표준 매뉴얼'\*\*에 맞춰 [기능 명] 기능을 구현해 주세요."

-----

## 🚀 다음 단계

이 매뉴얼을 파일(예: `ARCH_MANUAL.md`)로 저장하고 Antigravity 프로젝트 루트에 두시는 것을 권장합니다.

\*\*"이 매뉴얼을 바탕으로, 사용자 질문을 분석하여 '웹 검색'이 필요한지 '일반 대화'인지 판단하는 `Router` 노드와 그래프 코드를 작성해줘"\*\*라고 바로 요청해 보시겠습니까?
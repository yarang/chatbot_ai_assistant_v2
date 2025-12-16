# System Architecture

## 1. High-Level Architecture Overview

The system follows a **Layered Architecture** leveraging **FastAPI** for the interface, **LangGraph** for agent orchestration, and **PostgreSQL** for persistence.

```mermaid
graph TD
    subgraph "Clients"
        Telegram[Telegram Bot]
        Web[Web Dashboard]
        API[External API]
    end

    subgraph "Interface Layer (FastAPI)"
        TR[Telegram Router]
        WR[Web Router]
        QR[QA Router]
    end

    subgraph "Service Layer"
        CS[Conversation Service]
        KS[Knowledge Service]
        GS[Gemini Service]
    end

    subgraph "Agent Layer (LangGraph)"
        Graph[StateGraph Workflow]
        subgraph "Nodes"
            Sup[Supervisor]
            Res[Researcher]
            Gen[General Assistant]
            Not[Notion Search]
            Tool[Tools]
        end
    end

    subgraph "Data Layer"
        Repo[Repositories]
        DB[(PostgreSQL)]
    end

    Telegram --> TR
    Web --> WR
    API --> QR

    TR --> CS
    QR --> CS
    WR --> Repo
    WR --> KS

    CS --> Graph
    Graph --> Sup
    Sup --> Res
    Sup --> Gen
    Sup --> Not
    Res <--> Tool

    Res --> Sup
    Gen --> Sup
    Not --> Sup

    Nodes --> Repo
    Repo --> DB
```

## 2. Chat Request Flow (Telegram)

Detailed flow of how a message from Telegram is processed.

```mermaid
sequenceDiagram
    participant User
    participant Telegram
    participant TelegramRouter as API (TelegramRouter)
    participant Service as ConversationService
    participant Graph as LangGraph
    participant DB as Repository/DB

    User->>Telegram: Send Message
    Telegram->>TelegramRouter: Webhook Update
    TelegramRouter->>DB: Upsert User & ChatRoom
    TelegramRouter->>Service: ask_question_stream(user_id, room_id, question)
    
    Service->>Graph: ainvoke(initial_state)
    
    loop Graph Execution
        Graph->>Graph: retrieve_data_node (Load History)
        Graph->>Graph: Supervisor (Decide Next Step)
        
        alt Need Research
            Graph->>Graph: Researcher -> Tools -> Researcher -> Supervisor
        else General Chat
            Graph->>Graph: GeneralAssistant -> Supervisor
        else RAG
            Graph->>Graph: NotionSearch -> Supervisor
        end
        
        Graph->>Graph: FINISH -> save_conversation -> summarize
    end
    
    Graph-->>Service: Yield Chunks (Streaming)
    Service-->>TelegramRouter: Stream Token
    TelegramRouter-->>Telegram: Send/Edit Message
    Telegram-->>User: Display Response
```

## 3. LangGraph Workflow

The internal state machine of the AI agent.

```mermaid
stateDiagram-v2
    [*] --> retrieve_data
    retrieve_data --> Supervisor
    
    state Supervisor_Choice <<choice>>
    Supervisor --> Supervisor_Choice
    
    Supervisor_Choice --> Researcher: Next=Researcher
    Supervisor_Choice --> GeneralAssistant: Next=GeneralAssistant
    Supervisor_Choice --> NotionSearch: Next=NotionSearch
    Supervisor_Choice --> save_conversation: Next=FINISH
    
    Researcher --> Tools: Tool Call
    Tools --> Researcher
    Researcher --> Supervisor: Research Done
    
    GeneralAssistant --> Supervisor: Answer Generated
    
    NotionSearch --> Supervisor: Context Retrieved
    
    save_conversation --> summarize_conversation
    summarize_conversation --> [*]
```

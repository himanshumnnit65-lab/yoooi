# 🎪 Ringmaster Round Table v2.0 (TBuddy) - Comprehensive Architecture & Workflow Diagrams

This document provides complete, visual Mermaid diagrams explaining every architectural layer, execution flow, algorithmic optimization, and interaction model of the **TBuddy / Ringmaster Round Table v2.0** platform. These diagrams are designed to be used during technical interviews, system design presentations, and onboarding.

---

## 1. High-Level System Architecture (HLD)

This diagram illustrates the end-to-end architecture, showing how the Next.js client interacts with the FastAPI backend over HTTP and WebSockets, how state is managed in Upstash Redis, how parallel worker agents execute via Pub/Sub, and how the standardized Model Context Protocol (MCP) server provides tools to agents.

```mermaid
graph TB
    subgraph Client Layer ["🖥️ Client Layer (Next.js / React)"]
        UI["Trip Planner UI & Mapbox/Leaflet View"]
        WSClient["WebSocket Client (Live Progress Stream)"]
    end

    subgraph API Layer ["⚡ API Layer (FastAPI Stateless Backend)"]
        Router["API Routes (v1 / v2 HTTP Controllers)"]
        WSServer["WebSocket Endpoint (/ws/session)"]
        Auth["Google OAuth 2.0 / JWT Validator"]
        Orchestrator["Orchestrator Service (State & Timeout Manager)"]
    end

    subgraph State & Messaging ["🧠 State & Messaging Layer (Upstash Redis)"]
        RedisState[("Redis State Store<br>(HITLState & Session TTL)")]
        PubSub["Redis Pub/Sub Channels<br>(travel:tasks:*)"]
    end

    subgraph Worker Layer ["🚀 Parallel Worker Layer (Isolated Docker Containers)"]
        WeatherWorker["⛅ Weather Worker<br>(Sky Gazer)"]
        EventsWorker["🎟️ Events Worker<br>(Event Explorer)"]
        MapsWorker["🗺️ Maps Worker<br>(Trailblazer)"]
        BudgetWorker["💰 Budget Worker<br>(Quartermaster)"]
        ItineraryWorker["📅 Itinerary Worker<br>(Itinerary Weaver)"]
    end

    subgraph MCP & Tool Layer ["🛠️ Tool & MCP Standard Layer"]
        MCPServer["FastMCP Server (38 Custom Travel Tools over SSE)"]
        ORTools["Google OR-Tools<br>(TSP Math Solver)"]
    end

    subgraph External APIs ["🌐 External Providers & APIs"]
        LLM["Google Gemini & Groq Llama 3.3"]
        OpenWeather["OpenWeather API"]
        OpenWeb["OpenWeb Ninja API"]
        OpenRoute["OpenRouteService API"]
    end

    %% Client to API
    UI -->|HTTP POST /plan| Router
    WSClient <-->|Bi-directional WebSocket Stream| WSServer
    Router --> Auth
    Router --> Orchestrator

    %% API to Redis
    Orchestrator <-->|Read/Write Session State| RedisState
    Orchestrator -->|Publish Agent Tasks| PubSub
    WSServer <-->|Subscribe to Session Channels| PubSub

    %% Redis PubSub to Workers
    PubSub -->|travel:tasks:weather| WeatherWorker
    PubSub -->|travel:tasks:events| EventsWorker
    PubSub -->|travel:tasks:maps| MapsWorker
    PubSub -->|travel:tasks:budget| BudgetWorker
    PubSub -->|travel:tasks:itinerary| ItineraryWorker

    %% Workers to MCP & External Services
    WeatherWorker <-->|Dynamic Tool Binding| MCPServer
    EventsWorker <-->|Dynamic Tool Binding| MCPServer
    MapsWorker <-->|Dynamic Tool Binding| MCPServer
    BudgetWorker <-->|Dynamic Tool Binding| MCPServer
    ItineraryWorker <-->|Dynamic Tool Binding| MCPServer
    ItineraryWorker <-->|Geographic TSP Routing| ORTools

    WeatherWorker --> OpenWeather
    EventsWorker --> OpenWeb
    MapsWorker --> OpenRoute
    ItineraryWorker --> LLM
    WeatherWorker --> LLM
    EventsWorker --> LLM
```

---

## 2. Redis Parallel Worker & Pub/Sub Sequence Flow

Unlike sequential LLM pipelines that suffer from high latency, v2.0 executes domain agents concurrently. This sequence diagram shows how an incoming request is dispatched across Redis channels, processed simultaneously by containerized worker agents, and streamed back to the client in real time.

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 User / Next.js UI
    participant API as ⚡ FastAPI Orchestrator
    participant Redis as 🧠 Redis Pub/Sub & State
    participant W as ⛅ Weather Worker
    participant E as 🎟️ Events Worker
    participant B as 💰 Budget Worker
    participant I as 📅 Itinerary Worker

    User->>API: POST /api/v2/plan (destination, budget, preferences)
    API->>Redis: Initialize Session State (status=PROCESSING, TTL=3600s)
    API->>User: Return {session_id, status: "started"}
    
    User->>API: Connect WebSocket (/ws/session/{session_id})
    API->>Redis: Subscribe to "travel:streams:{session_id}"

    note over API,Redis: Broadcast Parallel Tasks to All Domain Workers
    par Parallel Agent Execution
        API->>Redis: PUBLISH travel:tasks:weather
        API->>Redis: PUBLISH travel:tasks:events
        API->>Redis: PUBLISH travel:tasks:budget
        API->>Redis: PUBLISH travel:tasks:itinerary
    end

    note over W,I: Workers Process Asynchronously & Stream Updates
    par Live Streaming Progress
        W->>Redis: PUBLISH travel:streams (type: "progress", msg: "Fetching 5-day forecast")
        Redis-->>User: WebSocket Stream: Weather progress
        E->>Redis: PUBLISH travel:streams (type: "progress", msg: "Scanning local events")
        Redis-->>User: WebSocket Stream: Events progress
        W->>Redis: PUBLISH travel:streams (type: "completed", data: WeatherData)
        Redis-->>User: WebSocket Stream: Weather completed
        
        B->>Redis: PUBLISH travel:streams (type: "completed", data: BudgetBreakdown)
        Redis-->>User: WebSocket Stream: Budget completed
        
        E->>Redis: PUBLISH travel:streams (type: "completed", data: EventsList)
        Redis-->>User: WebSocket Stream: Events completed

        I->>Redis: PUBLISH travel:streams (type: "progress", msg: "Weaving day-by-day schedule")
        I->>Redis: PUBLISH travel:streams (type: "completed", data: ItinerarySchedule)
        Redis-->>User: WebSocket Stream: Itinerary completed
    end

    note over API,Redis: Orchestrator Aggregates & Finalizes
    API->>Redis: Update OrchestratorState (status=COMPLETED, merged_data)
    Redis-->>User: WebSocket Stream: Trip Plan Ready!
```

---

## 3. Model Context Protocol (MCP) & Dynamic Tool Binding

To prevent LLM context window bloat and tool hallucination, TBuddy integrates an MCP standard server exposing 38 travel tools. Rather than injecting all 38 schemas into every prompt, agents query the FastMCP server at runtime, inspect schemas, and dynamically bind only the tools required for their specific task.

```mermaid
graph LR
    subgraph Agent Runtime ["🤖 BaseAgent Runtime (LangGraph StateGraph)"]
        Prompt["System Prompt & Task Goal"]
        ToolNode["LangGraph ToolNode<br>(Dynamic Tool Executor)"]
        LLMCall["LLM Engine<br>(Groq Llama 3.3 / Gemini)"]
    end

    subgraph MCP Client Layer ["🔌 MCP Client Adapter (app/mcp_client.py)"]
        Inspector["get_mcp_tools(filter_tags)"]
        HealthCheck["check_mcp_health()"]
    end

    subgraph MCP Server Layer ["🛠️ FastMCP Server (app/mcp_server.py over SSE)"]
        T_Flights["✈️ Flight Tools<br>(search_flights, get_prices)"]
        T_Hotels["🏨 Hotel Tools<br>(find_hotels, check_availability)"]
        T_Weather["⛅ Weather Tools<br>(get_forecast, radar)"]
        T_Routes["🗺️ Routing Tools<br>(calc_distance, get_polyline)"]
        T_Budget["💰 Finance Tools<br>(currency_convert, tax_calc)"]
        T_Events["🎟️ Event Tools<br>(search_concerts, exhibitions)"]
    end

    %% Execution Flow
    Prompt --> Inspector
    Inspector -->|1. Request Tools by Category/Tag| MCPServer
    MCPServer -->|2. Return Filtered JSON Schemas| Inspector
    Inspector -->|3. Bind Schemas to LLM| LLMCall
    LLMCall -->|4. Generate Tool Call Decision| ToolNode
    ToolNode -->|5. Execute over SSE / MCP Protocol| MCPServer

    MCPServer -.-> T_Flights
    MCPServer -.-> T_Hotels
    MCPServer -.-> T_Weather
    MCPServer -.-> T_Routes
    MCPServer -.-> T_Budget
    MCPServer -.-> T_Events
```

---

## 4. Human-in-the-Loop (HITL) State Machine & Feedback Loop

When a user interacts with the 5 high-impact features (Thumbs Up/Down, Budget Reallocation Sliders, Day/Activity Locks, Pre-Trip Preference Poll, or Swap Suggestions), the system updates the `HITLState` in Redis and performs targeted delta-regeneration without recomputing the entire trip.

```mermaid
stateDiagram-v2
    [*] --> InitialPlanGenerated: User Submits Trip Query
    
    state InitialPlanGenerated {
        state "Trip Schedule Displayed" as Display
        state "HITLState in Redis" as Memory
    }

    InitialPlanGenerated --> UserInteraction: User Triggers HITL Feature

    state UserInteraction {
        [*] --> ThumbsFeedback: 👍 / 👎 Activity
        [*] --> BudgetSlider: 🎚️ Adjust Ratios (e.g., Food +20%)
        [*] --> LockFeature: 🔒 Freeze Day 1 or Activity X
        [*] --> SwapAction: 🔄 Select Alternative Item
    }

    ThumbsFeedback --> StateMutation: Add to disliked_activities list
    BudgetSlider --> StateMutation: Update custom_budget_allocation
    LockFeature --> StateMutation: Add to locked_days / locked_activities
    SwapAction --> StateMutation: Apply replacement in itinerary_data

    state StateMutation {
        state "Persist Delta to Redis State Store" as RedisUpdate
    }

    StateMutation --> TargetedRegeneration: User Clicks 'Regenerate' or Apply

    state TargetedRegeneration {
        state "Construct Dynamic LLM System Instructions" as PromptInject
        state "Filter Out Locked Days/Activities" as FilterLocked
        state "Invoke Only Affected Worker Agents" as DeltaWorker
        state "Recalculate Route Geometry (OR-Tools)" as RouteReopt
        
        PromptInject --> FilterLocked
        FilterLocked --> DeltaWorker
        DeltaWorker --> RouteReopt
    }

    TargetedRegeneration --> InitialPlanGenerated: Publish Updated State via WebSocket
```

---

## 5. Algorithmic Routing & Hybrid Optimization (LLM + OR-Tools TSP)

LLMs are creative reasoning engines but fail at mathematical combinatorial optimization. TBuddy uses a **Hybrid Neuro-Symbolic Architecture**: the LLM selects theme-aligned activities, while Google OR-Tools solves the Traveling Salesperson Problem (TSP) to order locations geographically, minimizing travel time and distance.

```mermaid
flowchart TD
    subgraph Step 1: Creative Reasoning ["🧠 Step 1: Creative Reasoning (LLM)"]
        UserQuery["User Constraints & Preferences<br>(e.g., 3 Days Delhi, Nature 5/5, Culture 4/5)"]
        LLMSelect["Itinerary Weaver Agent<br>(Selects 10 Candidate Attractions per Day)"]
        CandidateList["Unordered Activity List with Lat/Long Coordinates"]
        
        UserQuery --> LLMSelect
        LLMSelect --> CandidateList
    end

    subgraph Step 2: Spatial Matrix Generation ["🗺️ Step 2: Spatial Matrix (OpenRouteService)"]
        CandidateList --> ORSCall["Call OpenRouteService Distance Matrix API"]
        Matrix["N x N Time & Distance Cost Matrix<br>(Travel time between every pair of coordinates)"]
        ORSCall --> Matrix
    end

    subgraph Step 3: Mathematical Optimization ["🧮 Step 3: TSP Combinatorial Solver (Google OR-Tools)"]
        Matrix --> ORSolver["Google OR-Tools Routing Model<br>(Objective: Minimize Total Travel Time)"]
        Constraints["Apply Hard Constraints:<br>- Locked Activities stay in fixed slots<br>- Lunch/Dinner within meal windows"]
        ORSolver --- Constraints
        SortedSequence["Geographic & Chronologically Ordered Schedule"]
        ORSolver --> SortedSequence
    end

    subgraph Step 4: Polyline Geometry & Rendering ["🎨 Step 4: Polyline Geometry (Frontend Map)"]
        SortedSequence --> PolylineCall["Fetch Turn-by-Turn GeoJSON Polylines"]
        FinalPayload["Publish Structured JSON to Redis"]
        PolylineCall --> FinalPayload
        FinalPayload --> LeafletMap["Render Interactive Markers & Polylines on Leaflet/Mapbox"]
    end
```

---

## 6. Frontend Real-Time Streaming & UI State Synchronization

This diagram maps out how the Next.js React frontend manages application state across live WebSocket messages, user UI interactions, and map updates without freezing the browser DOM.

```mermaid
graph TD
    subgraph External Events ["🔌 Incoming Network Streams"]
        WS["WebSocket Stream (/ws/session)"]
        HTTPResp["HTTP REST Responses"]
    end

    subgraph React State Layer ["⚛️ Next.js State Management (React Hooks / Context)"]
        SyncStore["Session Store (Zustand / React Context)"]
        AgentProgress["Agent Progress Map<br>{weather: 'completed', budget: 'progress'}"]
        ItineraryState["Active Itinerary Data<br>(Days, Activities, Costs)"]
        HITLLocal["Local HITL Controls<br>(Active Locks, Sliders, Dislikes)"]
    end

    subgraph UI Rendering Layer ["🖥️ UI Components & Map Visualization"]
        ProgressBadges["Live Worker Status Badges & Loading Bars"]
        DayCards["Day-by-Day Activity Cards<br>(With 👍/👎, 🔒 Lock, 🔄 Swap buttons)"]
        BudgetCharts["Dynamic Budget Reallocation Sliders & Charts"]
        MapContainer["Interactive Mapbox / Leaflet Component<br>(Markers, Tooltips, GeoJSON Polylines)"]
    end

    %% Event connections
    WS -->|Dispatch Event Type| SyncStore
    HTTPResp -->|Initial Load / Delta Apply| SyncStore

    SyncStore --> AgentProgress
    SyncStore --> ItineraryState
    SyncStore --> HITLLocal

    %% UI connections
    AgentProgress --> ProgressBadges
    ItineraryState --> DayCards
    ItineraryState --> MapContainer
    HITLLocal --> DayCards
    HITLLocal --> BudgetCharts

    %% User interaction loop
    DayCards -->|Click Lock / Dislike / Swap| HTTPResp
    BudgetCharts -->|Drag Slider & Apply| HTTPResp
```

---

## Summary of Diagram Use Cases for Interviews
1. **Use Diagram 1 (HLD)** when asked: *"Explain the architecture of your project and how frontend/backend communicate."*
2. **Use Diagram 2 (Redis Pub/Sub)** when asked: *"How do you reduce latency and handle concurrent AI tasks?"* or *"Why Redis?"*
3. **Use Diagram 3 (MCP)** when asked: *"How do your agents interact with external tools without overloading the LLM context window?"*
4. **Use Diagram 4 (HITL State Machine)** when asked: *"How do your interactive features (locks, feedback, budget sliders) work without regenerating everything?"*
5. **Use Diagram 5 (Hybrid OR-Tools TSP)** when asked: *"How do you ensure geographical routing accuracy and prevent AI hallucination in scheduling?"*
6. **Use Diagram 6 (Frontend State)** when asked: *"How do you handle real-time streaming and map updates in Next.js?"*

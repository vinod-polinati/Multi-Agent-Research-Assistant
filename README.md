# 🔬 Multi-Agent Research Assistant

A multi-agent AI system that autonomously researches any topic using web search, academic papers, and LLM-powered synthesis — all orchestrated by [LangGraph](https://github.com/langchain-ai/langgraph).

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2-purple)

---

## Architecture
```mermaid
graph TB
%% === STYLES ===
classDef core fill:#1E90FF,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px;
classDef db fill:#9ACD32,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px;
classDef external fill:#FFD700,stroke:#000,color:#000,stroke-width:2px,rx:10px,ry:10px;

%% === USERS ===
User(("User<br/>Submits Research Topic"))

%% === WEB API CONTAINER ===
subgraph "Web API Container"
  API["FastAPI Application<br/>main.py"]:::core
  DB["SQLite Database<br/>research.db"]:::db
end

User -->|"submits topic via REST API"| API
API -->|"creates job"| DB
API -->|"launches background task"| ResearchPipeline

%% === ORCHESTRATION CONTAINER ===
subgraph "Orchestration Container"
  Graph["StateGraph<br/>graph.py"]:::core
  Supervisor["Supervisor Node<br/>Generates Sub-Questions"]:::core
  WebResearcher["Web Researcher Node<br/>Uses Tavily API"]:::core
  PaperReader["Paper Reader Node<br/>Uses arXiv API"]:::core
  Critic["Critic Node<br/>Evaluates Research"]:::core
  Synthesizer["Synthesizer Node<br/>Generates Final Report"]:::core
end

ResearchPipeline -->|"executes graph"| Graph
Graph -->|"initializes state"| Supervisor
Supervisor -->|"triggers web search"| WebResearcher
WebResearcher -->|"appends results"| ResearchState
Supervisor -->|"triggers paper reading"| PaperReader
PaperReader -->|"appends summaries"| ResearchState
Supervisor -->|"triggers critique"| Critic
Critic -->|"generates follow-up queries"| Supervisor
Supervisor -->|"triggers report synthesis"| Synthesizer
Synthesizer -->|"stores report"| DB

%% === AGENTS ===
subgraph "Agent Modules"
  SupervisorAgent["Supervisor Agent<br/>agents/supervisor.py"]:::core
  WebResearcherAgent["Web Researcher Agent<br/>agents/web_researcher.py"]:::core
  PaperReaderAgent["Paper Reader Agent<br/>agents/paper_reader.py"]:::core
  CriticAgent["Critic Agent<br/>agents/critic.py"]:::core
  SynthesizerAgent["Synthesizer Agent<br/>agents/synthesizer.py"]:::core
end

Supervisor -->|"uses"| SupervisorAgent
WebResearcher -->|"uses"| WebResearcherAgent
PaperReader -->|"uses"| PaperReaderAgent
Critic -->|"uses"| CriticAgent
Synthesizer -->|"uses"| SynthesizerAgent

%% === STATE MANAGEMENT ===
subgraph "State Management"
  State["ResearchState<br/>state.py"]:::core
end

Graph -->|"updates shared state"| State

%% === EXTERNAL INTEGRATIONS ===
subgraph "External Integrations"
  Tavily["Tavily API<br/>Web Search"]:::external
  ArXiv["arXiv API<br/>Academic Papers"]:::external
end

WebResearcherAgent -->|"searches via"| Tavily
PaperReaderAgent -->|"fetches papers via"| ArXiv

%% === DATA FLOW ===
User -->|"receives report"| API
API -->|"streams progress updates"| User
Synthesizer -->|"final report accessible via API"| API
```
**Quick mode** (`⚡`) skips the Critic and goes straight to the Synthesizer.

---

## Tech Stack

| Layer      | Technology                         |
| ---------- | ---------------------------------- |
| Backend    | Python, FastAPI, LangGraph         |
| Resilience | Tenacity (retries), SlowAPI (rate limits) |
| Testing    | Pytest, Pytest-Asyncio             |
| LLMs       | Groq (Llama 3.3 70B via free tier) |
| Web Search | Tavily API (free tier)             |
| Papers     | ArXiv API + PyMuPDF                |
| Frontend   | Vanilla HTML + CSS + SSE           |
| Storage    | SQLite                             |

---

## Features & Resilience

- **Relevant Academic Research:** Strict semantic and arXiv-category filtering prevents irrelevant papers (like astronomy or computer vision) from polluting LLM reports.
- **Auto-Retries:** Transient failures with Groq, Tavily, or ArXiv APIs are automatically retried via `tenacity` with exponential backoff.
- **Security & Scale:** Built-in `slowapi` rate limiting (10 req/min/IP), strict maximum concurrency constraints, and user input sanitization to stop prompt injections.
- **Robust Orchestration:** LangGraph state machine ensures data is properly passed through `supervisor → web_researcher → paper_reader → critic → synthesizer` loops, intelligently determining if a topic needs deeper follow-up research. 

---

## Setup

### 1. Clone & enter the project

```bash
git clone <repo-url>
cd multiagent-research
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys

```bash
cp .env.example .env
```

Edit `.env` and add your keys:

| Key              | Where to get it                                         |
| ---------------- | ------------------------------------------------------- |
| `GROQ_API_KEY`   | [console.groq.com](https://console.groq.com) → API Keys |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) → Dashboard → API Keys |

### 5. Run

```bash
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** in your browser.

---

## API Endpoints

| Method | Endpoint                    | Description                        |
| ------ | --------------------------- | ---------------------------------- |
| POST   | `/research`                 | Start a research job               |
| GET    | `/research/{job_id}/stream` | SSE event stream for live progress |
| GET    | `/research/{job_id}/report` | Retrieve completed report          |
| POST   | `/research/{job_id}/export` | Download report as `.md` file      |

---

## v2 Roadmap

- [ ] Parallel agent execution via LangGraph `Send` API
- [ ] Vector store caching for previously researched topics
- [ ] Citation quality scoring
- [ ] User-configurable agent parameters
- [ ] Docker deployment

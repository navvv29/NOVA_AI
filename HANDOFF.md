# N.O.V.A — Handoff Document

> **Full name:** Navaneed's Operational Virtual Assistant
> **Short name:** Nova
> **Last updated:** 2026-08-25
> **Version:** 4.0 (Phase 4 — Always-On Companion)
> **Purpose:** Bring any new agent, platform, or developer up to speed instantly.

---

## TL;DR

N.O.V.A (Nova) is a **personal AI study companion** for CS/Engineering students. It's a Python app using LangGraph for the agent loop, Gemini/Groq for the LLM, FastAPI for the web server, and PostgreSQL for conversation memory.

**What's built across all phases:**
- **Phase 2:** Persistent memory, 10 tools, web UI, Docker deploy
- **Phase 3:** Performance tracker, multi-armed bandit (Thompson Sampling), adaptive recommendations, analytics dashboard, PWA
- **Phase 4 (NOW):** Always-on proactive mode, voice interaction, voice lock security, learning style profiler, career/academic growth tracker with XP system, SSE notifications, 34 total tools

---

## Architecture

```
User → Browser / Phone (PWA, voice-enabled)
         ↓
FastAPI (src/web.py) ─────────────────────────────────────┐
  ├─ /              → Chat UI (voice + text + always-on)   │
  ├─ /dashboard     → Analytics Dashboard (Chart.js)       │
  ├─ /api/chat      → Agent loop                           │
  ├─ /api/notifications → SSE push stream (proactive)      │
  ├─ /api/settings  → Always-on & security config          │
  └─ /api/analytics/* → Dashboard data APIs                │
         ↓                                                 │
LangGraph Agent (src/agent.py, 34 tools)                   │
  ├─ LLM: Gemini + Groq fallback (src/llm.py)             │
  ├─ System prompt adapts to learning profile               │
  └─ PostgreSQL checkpointer                               │
         ↓                                                 │
Tool Execution ────────────────────────────────────────────┘
  ├─ Core: web_search, datetime, file_ops
  ├─ Productivity: todo_manager
  ├─ Study: flashcards, quiz, summarizer, code_runner
  ├─ Performance: tracker, quiz_result, flashcard_review
  ├─ Adaptive: recommendation, rankings, bandit_insights
  ├─ Always-On: set_always_on, reminders, quiet_hours, name
  ├─ Security: voice_lock, voice_management, pin_code, session
  ├─ Profile: learning_profile, update_profile
  └─ Growth: skill, milestone, academic_goal, career_goal, xp
         ↓
Background Scheduler (src/always_on/scheduler.py)
  ├─ Checks flashcards, deadlines, streaks, weak topics
  ├─ Pushes notifications via SSE hub
  └─ Respects quiet hours, configurable intervals
         ↓
Analytics Engine (src/analytics/*)
  ├─ db.py    → SQLite schema (5 tables)
  ├─ queries.py → Read/write + dashboard aggregates
  └─ bandit.py  → Thompson Sampling (10 arms)
```

---

## Project Structure

```
├── HANDOFF.md                 ← YOU ARE HERE
├── requirements.txt           ← Python deps (no new deps for v4)
├── .env.example               ← Environment config
├── render.yaml                ← Render deployment
├── Dockerfile                 ← Container build
├── nova_flashcards.json       ← Flashcard data (runtime)
├── nova_todos.json            ← Todo data (runtime)
├── nova_analytics.db          ← Analytics SQLite DB (auto-created)
├── nova_learning_profile.json ← Learning style profile (auto-created)
├── nova_growth.json           ← Career/academic growth data
├── nova_security.json         ← Voice lock + PIN data
│
├── src/
│   ├── __init__.py
│   ├── agent.py               ← LangGraph graph + system prompt
│   ├── llm.py                 ← Gemini/Groq client with fallback
│   ├── main.py                ← CLI interface
│   ├── web.py                 ← FastAPI + all endpoints + SSE + scheduler
│   │
│   ├── web/
│   │   ├── index.html         ← Chat UI (voice, always-on, security panel)
│   │   ├── dashboard.html     ← Analytics dashboard
│   │   └── sw.js              ← Service worker
│   │
│   ├── analytics/             ← Performance tracking & bandit
│   │   ├── db.py              ← SQLite schema
│   │   ├── queries.py         ← Data access + aggregates
│   │   └── bandit.py          ← Thompson Sampling
│   │
│   ├── always_on/             ← NEW in v4.0
│   │   ├── scheduler.py       ← Background checks + SSE hub
│   │   ├── profiler.py        ← Learning style analysis
│   │   ├── security.py        ← Voice lock, PIN, sessions
│   │   └── growth.py          ← Skills, milestones, XP, goals
│   │
│   └── tools/                 ← 34 agent-callable tools
│       ├── __init__.py             ← Tool registry
│       ├── web_search.py
│       ├── datetime_tool.py
│       ├── file_operations.py
│       ├── todo_manager.py
│       ├── flashcards.py
│       ├── quiz.py
│       ├── summarizer.py
│       ├── code_runner.py
│       ├── performance_tracker.py
│       ├── adaptive_recommender.py
│       └── always_on_tools.py  ← NEW: always-on, security, growth
│
└── tests/
    └── test_tools.py
```

---

## The 34 Tools

| # | Tool | Category | Purpose |
|---|------|----------|---------|
| 1 | `web_search` | Core | DuckDuckGo search |
| 2 | `get_current_datetime` | Core | Current date/time |
| 3 | `read_file` | Core | Read files |
| 4 | `write_file` | Core | Write files |
| 5 | `list_files` | Core | List directories |
| 6 | `manage_todo` | Productivity | Task management |
| 7 | `manage_flashcards` | Study | Flashcards + SM-2 |
| 8 | `generate_quiz` | Study | Quiz generation |
| 9 | `summarize_text` | Study | Text summarization |
| 10 | `run_code` | Code | Python sandbox |
| 11 | `track_study_session` | Analytics | Log study sessions |
| 12 | `record_quiz_result` | Analytics | Log quiz scores |
| 13 | `record_flashcard_review_result` | Analytics | Log card reviews |
| 14 | `get_performance_report` | Analytics | Performance summary |
| 15 | `get_study_recommendation` | Adaptive | Bandit recommendation |
| 16 | `get_method_rankings` | Adaptive | Method rankings |
| 17 | `get_bandit_insights` | Adaptive | Bandit diagnostics |
| 18 | `set_always_on` | Always-On | Toggle proactive mode |
| 19 | `get_always_on_status` | Always-On | Check status |
| 20 | `set_reminder_interval` | Always-On | Reminder frequency |
| 21 | `set_quiet_hours` | Always-On | Notification silence |
| 22 | `set_preferred_name` | Always-On | Personalization |
| 23 | `enable_voice_lock` | Security | Toggle voice auth |
| 24 | `manage_voice` | Security | Authorized voices |
| 25 | `set_pin_code` | Security | Backup PIN |
| 26 | `create_access_session` | Security | Session tokens |
| 27 | `get_learning_profile` | Profiler | Learning style data |
| 28 | `update_learning_profile` | Profiler | Refresh profile |
| 29 | `manage_skill` | Growth | Track skills + XP |
| 30 | `manage_milestone` | Growth | Record achievements |
| 31 | `manage_academic_goal` | Growth | Academic targets |
| 32 | `manage_career_goal` | Growth | Career objectives |
| 33 | `get_growth_report` | Growth | Growth overview |
| 34 | `earn_xp` | Growth | Award XP |

---

## Key Systems Explained

### Always-On Mode (`src/always_on/scheduler.py`)
- Background asyncio loop checks every 60 seconds
- When enabled: monitors flashcard due dates, deadlines, streak maintenance, weak topics
- Notifications pushed to browser via **Server-Sent Events** (SSE)
- Configurable quiet hours (default 11PM-7AM), reminder interval (15-120 min)
- Broadcast hub supports multiple connected clients

### Voice Interaction (Browser-based, no API key needed)
- **STT (Speech-to-Text):** Web Speech API (`webkitSpeechRecognition`)
- **TTS (Text-to-Speech):** Web Speech Synthesis API
- **Voice Lock:** Voice fingerprinting via audio feature hashing (SHA-256)
  - Register authorized voices by label
  - Only registered fingerprints can access the agent when lock is enabled
  - PIN code as backup authentication
  - Lockout after failed attempts

### Learning Style Profiler (`src/always_on/profiler.py`)
- Analyzes method effectiveness data to build a learning profile
- Dimensions: Visual↔Text, Active↔Passive, Collaborative↔Focused
- Determines preferred study time, optimal session length
- Classifies teaching style: Socratic, Example-First, Theory-First, Adaptive
- Profile injected into agent system prompt for personalized responses

### Career & Academic Growth (`src/always_on/growth.py`)
- **XP System:** Earn XP for study sessions (10), quiz passes (20-50), streaks (5/day)
- **Levels:** 10+ level thresholds (50, 150, 300, 500, 800, 1200, ...)
- **Skills:** Track proficiency per skill with XP and level
- **Milestones:** Record career/academic achievements
- **Goals:** Academic (GPA, courses) and career (internships, roles) targets

### Multi-Armed Bandit (`src/analytics/bandit.py`)
- Thompson Sampling with Beta(α, β) posteriors
- 10 study method arms
- Rewards from quiz scores, flashcard ratings, self-reported confidence
- Balances exploration vs exploitation automatically

---

## API Endpoints

### Chat & Notifications
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send message, get response |
| POST | `/api/new` | Start new conversation |
| GET | `/api/history` | Conversation history |
| GET | `/api/notifications` | SSE push stream |

### Settings & Security
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/settings` | Get user settings |
| POST | `/api/settings` | Update settings |
| GET | `/api/learning-profile` | Get learning profile |

### Analytics
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/analytics/overview` | Summary stats |
| GET | `/api/analytics/topics` | Time by topic |
| GET | `/api/analytics/methods` | Method effectiveness |
| GET | `/api/analytics/progress` | Scores over time |
| GET | `/api/analytics/streak` | Study streak |
| GET | `/api/analytics/weak-topics` | Weak areas |
| GET | `/api/analytics/bandit/rankings` | Method rankings |
| GET | `/api/analytics/bandit/suggest` | Top bandit picks |

---

## Environment Variables

```env
GEMINI_API_KEY=...           # Primary LLM (free tier)
GROQ_API_KEY=...             # Fallback LLM (free tier)
PRIMARY_PROVIDER=gemini
DATABASE_URL=postgresql://localhost:5432/nova
NOVA_ANALYTICS_DB=nova_analytics.db
```

---

## Running Locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # Add API keys

# Web UI (recommended)
python -m src.web
# → http://localhost:8000      (chat + voice)
# → http://localhost:8000/dashboard (analytics)

# CLI
python -m src.main
```

---

## Cloud Deployment (Free Tier)

### Google Cloud Platform (Free)

**Option 1: Cloud Run (Recommended)**
```bash
# Install gcloud CLI
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build and deploy
gcloud run deploy nova --source . --platform managed --region us-central1 --allow-unauthenticated

# Set env vars
gcloud run services update nova \
    --set-env-vars GEMINI_API_KEY=xxx,GROQ_API_KEY=xxx,DATABASE_URL=xxx
```
- **Free tier:** 180,000 vCPU-seconds/month, 2 GB memory, 1 GB outbound
- Always-on HTTP service, auto-scales to zero
- Use Cloud SQL (PostgreSQL) free tier for persistent memory

**Option 2: Compute Engine (e2-micro)**
```bash
# Create free e2-micro instance (always-free tier)
gcloud compute instances create nova-server \
    --zone=us-central1-a \
    --machine-type=e2-micro \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --scopes=default

# SSH in, install deps, run with systemd
```
- **Always free:** 1 non-shared CPU, 1 GB RAM (us regions)
- Good for always-on mode since it doesn't scale to zero

**Option 3: App Engine (Standard)**
```bash
gcloud app deploy
```
- Free tier: 28 instance-hours/day for F1 instances
- Auto-scales, but may have cold start delays

### Microsoft Azure (Free)

**Option 1: Azure Container Apps (Recommended)**
```bash
# Install Azure CLI
az login
az containerapp up nova --source . --resource-group mygroup --environment myenv
```
- **Free tier:** 180,000 vCPU-seconds/month, 360 GB-seconds memory
- Serverless containers, auto-scales to zero

**Option 2: Azure B1S VM**
```bash
# Create B1S VM (always-free tier)
az vm create --resource-group mygroup --name nova \
    --image Ubuntu2204 --size Standard_B1s \
    --admin-username azureuser --generate-ssh-keys
```
- **Always free:** 750 hours/month B1S (1 vCPU, 1 GB RAM)
- 128 GB managed disk included

**Option 3: Azure Static Web Apps + Container Apps**
- Free SSL, custom domains, CI/CD from GitHub

### Database on Cloud (Free)

**Render PostgreSQL:**
- Free tier: 90 days, then $7/month
- Auto-creates with `render.yaml`

**Supabase (PostgreSQL):**
- Free tier: 500 MB, always free
- `DATABASE_URL=postgresql://xxx@xxx.supabase.co:5432/postgres`

**Neon (PostgreSQL):**
- Free tier: 0.5 GB storage, always free
- Auto-pause when inactive (good for dev)

**TiDB Serverless:**
- Free tier: 5 GB storage, always free
- MySQL-compatible but works with most ORMs

### Recommended Free Stack
```
App:       Cloud Run / Container Apps (free tier)
Database:  Supabase or Neon (always free)
LLM:       Gemini + Groq (free API tiers)
Frontend:  Served by FastAPI (no separate hosting needed)
```

---

## Data Stores

| Store | Engine | Purpose | File |
|-------|--------|---------|------|
| Memory | PostgreSQL | LangGraph checkpointer | `DATABASE_URL` |
| Analytics | SQLite | Performance + bandit | `nova_analytics.db` |
| Flashcards | JSON | SM-2 spaced repetition | `nova_flashcards.json` |
| Todos | JSON | Task management | `nova_todos.json` |
| Profile | JSON | Learning style | `nova_learning_profile.json` |
| Growth | JSON | Career/academic goals | `nova_growth.json` |
| Security | JSON | Voice lock + PIN | `nova_security.json` |

---

## Testing

```bash
python -m pytest tests/ -v
python -m src.web    # Manual test
```

---

## Future Work (Phase 5 Ideas)

- [ ] Proper speaker verification model (instead of fingerprint hashing)
- [ ] WebSocket for real-time bidirectional chat
- [ ] Import Anki decks
- [ ] Export analytics to CSV/PDF
- [ ] Calendar integration (Google Calendar API)
- [ ] Email digest of daily progress
- [ ] Pomodoro timer with auto-session recording
- [ ] Knowledge graph visualization
- [ ] Multi-user / team study mode
- [ ] Browser extension for context-aware help
- [ ] Offline-capable with full sync

---

*This document is the single source of truth for project status. Update it when making significant changes.*

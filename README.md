# N.O.V.A — Navaneed's Operational Virtual Assistant

Your private, adaptive AI companion for studying, coding, and building projects. Built for a CS/Engineering college student. 100% free to run. No data sharing.

## What is N.O.V.A?

N.O.V.A (Nova) is a personal AI study companion that:
- **Learns how you learn** — adapts teaching style to your patterns
- **Tracks your progress** — performance analytics, XP system, skill levels
- **Stays proactive** — reminds you of reviews, deadlines, and streaks
- **Responds to your voice** — speech input, voice lock security
- **Protects your data** — everything runs locally, no data sharing

## Features

### Core
- Persistent memory across sessions (PostgreSQL)
- Web search, file operations, code execution
- Task management with priorities and deadlines

### Study Tools
- Flashcards with SM-2 spaced repetition
- Quiz generation (MCQ, true/false, mixed)
- Text summarization
- Performance tracking with analytics dashboard

### Adaptive Learning
- **Multi-armed bandit** (Thompson Sampling) learns which study methods work best
- 10 study methods tracked: flashcards, active recall, pomodoro, interleaving, elaboration, practice problems, mind mapping, teach back, Cornell notes, retrieval practice
- Personalized study recommendations based on your data

### Always-On Mode
- Background scheduler monitors flashcards, deadlines, streaks
- Push notifications via Server-Sent Events
- Configurable quiet hours and reminder intervals
- Voice lock security with PIN backup

### Growth System
- XP and leveling for study achievements
- Skill tracking with proficiency levels
- Career and academic goal management
- Milestone recording

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### Configure `.env`

```env
GEMINI_API_KEY=your_key_here    # https://aistudio.google.com/apikey
GROQ_API_KEY=your_key_here      # https://console.groq.com/keys
PRIMARY_PROVIDER=gemini
DATABASE_URL=postgresql://localhost:5432/nova
```

## Run

```bash
python -m src.web
# Open http://localhost:8000
```

## Architecture

```
User → Browser/Phone (PWA)
         ↓
FastAPI → LangGraph Agent (34 tools) → LLM (Gemini/Groq)
         ↓                    ↓
   PostgreSQL            Analytics (SQLite)
   (memory)         + Always-On Scheduler
```

## Deploy (Free)

See [HANDOFF.md](HANDOFF.md) for GCP/Azure free tier deployment guides.

## Documentation

See [HANDOFF.md](HANDOFF.md) for complete project documentation, API reference, and handoff guide for other agents/platforms.

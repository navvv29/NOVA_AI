# N.O.V.A - Complete Build Documentation

> How N.O.V.A was built from scratch, step by step.
> Written so you can learn every decision, every file, every line.

---

## 1. What Was There Before

The project started as Jarvis - a basic AI chatbot with 10 tools:
web_search, datetime, file_ops, todos, flashcards, quiz, summarizer, code_runner.

It could chat, search web, manage todos, flashcards, quizzes, run code.
It could NOT track performance, learn from data, recommend study methods, speak, send notifications, or adapt to the user.

---

## 2. Phase 1: Analytics Database (src/analytics/db.py)

Why: To build adaptive learning, needed a place to store study data.
SQLite chosen - no server needed, file-based, works everywhere.

5 tables created:
- study_sessions: When you studied, what method, how long, confidence
- quiz_attempts: Quiz scores, difficulty, method used
- flashcard_reviews: Card ratings, ease factor, intervals
- method_rewards: Bandit rewards per method
- learning_goals: Target scores per topic

Key: init_db() runs automatically on import. No manual setup needed.

---

## 3. Phase 2: Multi-Armed Bandit (src/analytics/bandit.py)

Why: The user studies using different methods. Some work better than others.
A multi-armed bandit learns which method works best for THIS specific user.

Algorithm: Thompson Sampling
- 10 slot machines (study methods), each with hidden payout rate
- Balances exploration (trying new methods) vs exploitation (using best)
- Uses Beta distribution: alpha = successes, beta = failures

The 10 arms:
flashcards, active_recall, pomodoro, interleaving, elaboration,
practice_problems, mind_mapping, teach_back, cornell_notes, retrieval_practice

Reward sources:
- Quiz score: 80% = 0.8 reward
- Flashcard: easy=1.0, good=0.75, hard=0.4, again=0.1
- Confidence: 4/5 = 0.75

---

## 4. Phase 3: Agent Tools (src/tools/)

Why: The AI agent needs tools to interact with the analytics system.
Each tool is a Python function with @tool decorator that LangGraph can call.

7 new tools:
- track_study_session: Logs sessions to SQLite and feeds bandit
- record_quiz_result: Logs quiz scores to SQLite and feeds bandit
- record_flashcard_review_result: Logs reviews to SQLite and feeds bandit
- get_performance_report: Shows stats from all tables
- get_study_recommendation: Suggests method via Thompson Sampling
- get_method_rankings: Shows all method scores
- get_bandit_insights: Raw bandit diagnostics

Tools register in src/tools/__init__.py by adding to TOOLS list.
LangGraph auto-binds all tools to the LLM.

---

## 5. Phase 4: Web Dashboard (src/web/dashboard.html)

Why: Visual charts make learning progress immediately obvious.

Built with Chart.js (CDN, no install):
- Line chart: quiz scores over time
- Doughnut chart: study time by topic
- Bar chart: method effectiveness
- Stats cards: streak, sessions, study time, scores
- Period selector: 7/30/90 days

8 API endpoints added to web.py for dashboard data.

---

## 6. Phase 5: PWA Support

Why: Make it installable on phones like a native app.

Added:
- Service Worker (sw.js): caches static assets for offline use
- Manifest (via web.py): app name, icons, theme color
- Meta tags: apple-mobile-web-app-capable, theme-color

Install: Open in Chrome mobile, menu, Add to Home Screen

---

## 7. Phase 6: Always-On Mode (src/always_on/scheduler.py)

Why: Make Nova proactive, not just reactive.

Architecture:
Browser (SSE) connects to FastAPI (/api/notifications) connects to NotificationHub connects to Scheduler

Scheduler checks periodically:
- Flashcard due dates (every 30 min)
- Deadline alerts (every 6 hours)
- Study streak (every hour)
- Weak topics (every 12 hours)
- Bandit suggestions (every 4 hours)

SSE = Server-Sent Events: persistent HTTP connection for real-time push.

---

## 8. Phase 7: Voice Interaction

Three components:

1. STT: Web Speech API (built into Chrome, free)
   - continuous=true, interimResults=true
   - Shows words as you speak in real-time

2. TTS: SpeechSynthesis API
   - rate=0.92 for soft, calm feel
   - Auto-picks soft female voice (Samantha/Zira/Karen)

3. Conversation Loop:
   Speak, STT, 1.5s silence, auto-send, Nova responds, TTS speaks, listen again

Debounce pattern: timer-based, not event-based (more reliable in Chrome)

---

## 9. Phase 8: Security (src/always_on/security.py)

Three layers:
1. Voice Lock: SHA-256 fingerprint hashes for authorized voices
2. PIN Code: 4-8 digits, stored as SHA-256 hash (never plaintext)
3. Session Tokens: 8-hour tokens, auto-expire

---

## 10. Phase 9: Learning Profiler (src/always_on/profiler.py)

Tracks 5 dimensions from study data:
- Visual vs Text preference
- Active vs Passive learning
- Collaborative vs Focused
- Preferred study time
- Optimal session length

Classifies teaching style:
- active > 0.65 = Socratic (question-driven)
- visual > 0.6 = Example-first
- text > 0.6 = Theory-first
- Otherwise = Adaptive

Profile injected into agent system prompt for real-time adaptation.

---

## 11. Phase 10: Career Growth (src/always_on/growth.py)

XP System:
- 10 XP per session, 20-50 per quiz, 5 per streak day
- Levels: 50, 150, 300, 500, 800, 1200, 1800, 2500, 3500, 5000

Three goal types:
- Academic: GPA targets, course completion
- Career: Internships, roles, required skills
- Skill: Proficiency tracking with XP and level

---

## 12. Phase 11: Rebrand to N.O.V.A

Jarvis became N.O.V.A (Navaneed Operational Virtual Assistant)
Updated 20+ files: agent.py, web.py, index.html, dashboard.html,
sw.js, main.py, render.yaml, Dockerfile, .env, .gitignore, docs

---

## 13. Phase 12: UI Redesign

From generic chat to futuristic interface:
- Dark theme with grid background and glowing blue accents
- Sidebar with navigation and live stats
- Animated welcome orb with float animation
- Smooth cubic-bezier message animations
- Toast notifications, mobile responsive

---

## 14. Phase 13: Voice Conversation Mode

JARVIS experience:
Always-On, Nova listens, You speak, 1.5s silence, auto-send,
Nova processes, Nova speaks, Nova listens again, repeat

Clap detection: Web Audio API monitors mic volume.
Phone notifications: Browser Push Notification API.

---

## 15. How Everything Connects

Full data flow:
User: I studied binary trees with flashcards for 30 min
Agent calls track_study_session
Tool writes to SQLite and computes reward
Bandit updates Beta distribution
Next recommendation: Try active_recall (72% success)

Tech Stack:
- Frontend: HTML + CSS + JavaScript (vanilla, no framework)
- Backend: Python + FastAPI
- AI: LangGraph + Gemini/Groq
- Database: SQLite (analytics) + PostgreSQL (memory, optional)
- Charts: Chart.js (CDN)
- Voice: Web Speech API (browser built-in)
- PWA: Service Worker + Manifest

---

## Key Lessons

1. Start simple, iterate - 10 tools became 34 tools
2. Data drives intelligence - track everything
3. Browser APIs are powerful - voice, notifications, PWA = free
4. Fallback gracefully - PostgreSQL fails? SQLite. Gemini out? Groq.
5. UI matters - same features, different UI = different experience
6. Security is layers - voice + PIN + tokens

---

Written by Codebuff while building N.O.V.A on August 25, 2026.
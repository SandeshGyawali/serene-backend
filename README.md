# Serene Backend

FastAPI backend for the Serene mental health companion app. Handles user sessions, AI-powered chat via Google Gemini, conversation analysis, and task management.

## Setup

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example below into a `.env` file at the project root and fill in your API keys:

```env
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=sqlite:///./serene.db
PROCESS_START_DATE=2024-01-01
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

> **Gemini API key**: Get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Make sure the key belongs to a project with billing enabled.
>
> **OpenAI API key**: Used for Whisper speech-to-text on voice messages. Optional if you are not using voice.

### 4. Run the server

```bash
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at `http://127.0.0.1:8000`.

Interactive docs: `http://127.0.0.1:8000/docs`

---

## Project Structure

```
serene-backend/
├── main.py                  # App entry point
├── requirements.txt
├── .env                     # Environment variables (not committed)
├── serene.db                # SQLite database (auto-created on first run)
├── local_data/
│   └── session/             # Per-conversation JSON session files
└── app/
    ├── core/
    │   ├── config.py        # Settings loaded from .env
    │   └── database.py      # SQLAlchemy engine + session
    ├── models/
    │   ├── db_models.py     # SQLAlchemy table definitions
    │   └── schemas.py       # Pydantic request/response schemas
    ├── endpoints/
    │   ├── user.py          # /api/v1/user, /progress, /stats/process
    │   ├── tasks.py         # /api/v1/tasks
    │   ├── daily.py         # /api/v1/daily
    │   ├── chat.py          # /api/v1/chat, /voice, /history, /sessions
    │   ├── completions.py   # /v1/chat/completions, /v1/session/new|end
    │   └── admin.py         # /api/v1/admin/*, /api/v1/stats/mental
    ├── service/
    │   ├── user_service.py
    │   ├── task_service.py
    │   ├── daily_service.py
    │   ├── oracle_service.py       # Gemini AI calls
    │   ├── analysis_service.py     # Conversation analysis via Gemini
    │   └── session_file_service.py # JSON session file management
    └── utils/
        ├── oracle_prompt.py  # System prompt for the AI companion
        └── time_utils.py     # XP calculation, level, timing helpers
```

---

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/user/{username}` | Get user profile and level |
| `GET` | `/api/v1/daily/{username}/plan` | Today's task schedule |
| `POST` | `/api/v1/daily/{username}/complete` | Mark a task complete, earn XP |
| `POST` | `/v1/session/new` | Start a new conversation session |
| `POST` | `/v1/chat/completions` | Chat with Serene AI (OpenAI-compatible) |
| `POST` | `/v1/session/end` | End session and trigger analysis |
| `POST` | `/api/v1/sessions/{username}/{id}/analyze` | Analyze a conversation with AI |
| `GET` | `/api/v1/stats/mental/{username}` | Mental health stats for the user |
| `GET` | `/api/v1/admin/users` | All users (admin) |
| `GET` | `/api/v1/admin/analyses` | All session analyses (admin) |
| `GET` | `/health` | Health check |

---

## Database

SQLite database is created automatically at `serene.db` on first run. Tables:

- `users` — user profiles and XP
- `tasks` — scheduled tasks (default + custom)
- `daily_logs` — per-day task execution tracking
- `chat_messages` — all messages per session
- `sessions` — conversation session metadata
- `conversation_analyses` — AI-generated insights from ended sessions

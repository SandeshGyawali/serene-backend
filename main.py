from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from app.core.config import get_settings
from app.core.database import init_db
from app.endpoints import user, tasks, daily, chat, completions, admin

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Serene Backend — The Oracle",
    description="Backend for the Serene life-RPG app. Manages tasks, XP, streaks, and the Oracle AI.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
        *settings.origins_list,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

audio_dir = Path(__file__).resolve().parent / "local_data" / "audio"
audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media/audio", StaticFiles(directory=str(audio_dir)), name="audio")

app.include_router(user.router)
app.include_router(tasks.router)
app.include_router(daily.router)
app.include_router(chat.router)
app.include_router(completions.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "serene-backend"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

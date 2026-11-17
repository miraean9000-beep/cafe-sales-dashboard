import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.routes import router
from app.seed import seed
from app.storage import store

load_dotenv()


def initialize():
    database = store()
    if os.getenv("STORAGE", "sqlite") == "sqlite" and not database.get("settings", "seed"):
        seed(database)
        database.create("settings", {"id": "seed"})


@asynccontextmanager
async def lifespan(app):
    if os.getenv("RENDER") and (os.getenv("STORAGE") != "firestore" or not os.getenv("APP_TOKEN")):
        raise RuntimeError("Render requires STORAGE=firestore and APP_TOKEN")
    await run_in_threadpool(initialize)
    yield


app = FastAPI(title="Maven Roasters 매출 비서", version="1.0.0", lifespan=lifespan)
origins = [part.strip() for part in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if part.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "PUT", "DELETE"],
                   allow_headers=["Authorization", "Content-Type"])
app.include_router(router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory=Path(__file__).parent / "frontend", html=True), name="frontend")

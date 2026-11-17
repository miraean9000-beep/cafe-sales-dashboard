import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.routes import cloud_runtime, router
from app.seed import seed
from app.storage import store

if not cloud_runtime():
    load_dotenv()


def initialize():
    database = store()
    if os.getenv("STORAGE", "sqlite") == "sqlite" and not database.get("settings", "seed"):
        seed(database)
        database.create("settings", {"id": "seed"})


@asynccontextmanager
async def lifespan(app):
    if not os.getenv("VERCEL"):
        if cloud_runtime() and (os.getenv("STORAGE") != "firestore" or not os.getenv("APP_TOKEN", "").strip()):
            raise RuntimeError("Cloud deployment requires STORAGE=firestore and APP_TOKEN")
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


FRONTEND = Path(__file__).resolve().parent / "frontend"


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND / "index.html")


@app.get("/{asset}", include_in_schema=False)
def frontend_asset(asset: str):
    if asset not in {"app.js", "config.js", "style.css"}:
        raise HTTPException(404)
    return FileResponse(FRONTEND / asset)

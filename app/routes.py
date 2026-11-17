import os
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .analysis import summarize
from .chat import ai_configured, answer
from .models import Chat, Conversation, Sale
from .storage import store

bearer = HTTPBearer(auto_error=False)


def cloud_runtime():
    return bool(os.getenv("VERCEL") or os.getenv("RENDER"))


def authorize(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    token = os.getenv("APP_TOKEN", "").strip()
    if cloud_runtime() and (not token or os.getenv("STORAGE") != "firestore"):
        raise HTTPException(503, "서버의 Firestore 및 접속 토큰 설정이 필요합니다.")
    if token and (
        not credentials or not secrets.compare_digest(credentials.credentials.encode(), token.encode())
    ):
        raise HTTPException(401, "유효한 접속 토큰을 입력해 주세요.", headers={"WWW-Authenticate": "Bearer"})


router = APIRouter(prefix="/api", dependencies=[Depends(authorize)])


def check_id(key):
    if not key.isascii() or not key.replace("-", "").isalnum() or len(key) > 64:
        raise HTTPException(404, "기록을 찾을 수 없습니다.")


@router.get("/status", tags=["system"])
def status():
    return {"storage": os.getenv("STORAGE", "sqlite"), "ai": ai_configured()}


@router.post("/data", status_code=201, tags=["sales"])
def add_sale(sale: Sale):
    item = {"id": uuid4().hex, **sale.model_dump(mode="json")}
    store().create("data", item)
    return item


@router.get("/data", tags=["sales"])
def list_sales():
    return sorted(store().list("data"), key=lambda item: (item["date"], item["id"]), reverse=True)


@router.get("/data/summary", tags=["sales"])
def summary():
    return summarize(store().list("data"))


@router.put("/data/{key}", tags=["sales"])
def update_sale(key: str, sale: Sale):
    check_id(key)
    item = {"id": key, **sale.model_dump(mode="json")}
    if not store().update("data", item):
        raise HTTPException(404, "매출 기록을 찾을 수 없습니다.")
    return item


@router.delete("/data/{key}", status_code=204, tags=["sales"])
def delete_sale(key: str):
    check_id(key)
    if not store().delete("data", key):
        raise HTTPException(404, "매출 기록을 찾을 수 없습니다.")


def save(messages):
    item = {
        "id": uuid4().hex, "title": messages[0]["content"][:80],
        "created_at": datetime.now(timezone.utc).isoformat(), "messages": messages,
    }
    store().create("conversations", item)
    return item


@router.post("/conversations", status_code=201, tags=["conversations"])
def save_conversation(conversation: Conversation):
    return save(conversation.model_dump()["messages"])


@router.get("/conversations", tags=["conversations"])
def list_conversations():
    rows = sorted(store().list("conversations"), key=lambda row: row["created_at"], reverse=True)
    return [{key: row[key] for key in ("id", "title", "created_at")} for row in rows]


@router.get("/conversations/{key}", tags=["conversations"])
def get_conversation(key: str):
    check_id(key)
    item = store().get("conversations", key)
    if not item:
        raise HTTPException(404, "대화 기록을 찾을 수 없습니다.")
    return item


@router.delete("/conversations/{key}", status_code=204, tags=["conversations"])
def delete_conversation(key: str):
    check_id(key)
    if not store().delete("conversations", key):
        raise HTTPException(404, "대화 기록을 찾을 수 없습니다.")


@router.post("/chat", tags=["chat"])
def chat(request: Chat):
    messages = request.model_dump()["messages"]
    reply = answer(summary(), messages)
    conversation = save([*messages, {"role": "assistant", "content": reply}])
    return {"answer": reply, "conversation": conversation}

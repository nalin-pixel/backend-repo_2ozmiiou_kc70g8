import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import TattooService, PortfolioItem, Appointment, BotSession, AdminLogin

app = FastAPI(title="Tattoo Artist API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utils
class ObjectIdStr(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        try:
            return str(ObjectId(str(v)))
        except Exception:
            raise ValueError("Invalid ObjectId")


def get_admin_secret():
    secret = os.getenv("ADMIN_PASSWORD", "admin123")
    return secret


def require_admin(password: str):
    if password != get_admin_secret():
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
def root():
    return {"message": "Tattoo Artist Backend is running"}


@app.get("/schema")
def schema_overview():
    return {
        "tattooservice": TattooService.model_json_schema(),
        "portfolioitem": PortfolioItem.model_json_schema(),
        "appointment": Appointment.model_json_schema(),
        "botsession": BotSession.model_json_schema(),
    }


# Public content endpoints
@app.get("/services")
def list_services():
    items = get_documents("tattooservice", {"is_active": True})
    for it in items:
        it["id"] = str(it.pop("_id"))
    return items


@app.get("/portfolio")
def list_portfolio():
    items = get_documents("portfolioitem", {})
    for it in items:
        it["id"] = str(it.pop("_id"))
    return items


class AppointmentCreate(Appointment):
    pass


@app.post("/appointments")
def create_appointment(payload: AppointmentCreate):
    data = payload.model_dump()
    inserted_id = create_document("appointment", data)
    return {"id": inserted_id}


# Admin endpoints (simple password check)
class AdminAuth(BaseModel):
    password: str


@app.get("/admin/appointments")
def admin_list_appointments(password: str):
    require_admin(password)
    items = get_documents("appointment", {})
    for it in items:
        it["id"] = str(it.pop("_id"))
    return items


@app.post("/admin/services")
def admin_add_service(payload: TattooService, password: str):
    require_admin(password)
    inserted_id = create_document("tattooservice", payload)
    return {"id": inserted_id}


@app.post("/admin/portfolio")
def admin_add_portfolio(payload: PortfolioItem, password: str):
    require_admin(password)
    inserted_id = create_document("portfolioitem", payload)
    return {"id": inserted_id}


# Telegram Bot webhook style endpoint (simple stateful flow)
class TelegramUpdate(BaseModel):
    message_text: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None


@app.post("/bot/update")
def bot_update(update: TelegramUpdate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    user_id = update.user_id
    if user_id is None:
        raise HTTPException(status_code=400, detail="user_id required")

    # find or create session
    session = db["botsession"].find_one({"telegram_user_id": user_id})
    if not session:
        session_id = create_document("botsession", {
            "telegram_user_id": user_id,
            "state": "ask_name",
            "data": {},
        })
        session = db["botsession"].find_one({"_id": ObjectId(session_id)})
        reply = "Привет! Как тебя зовут?"
        return {"reply": reply, "state": session.get("state")}

    state = session.get("state", "ask_name")
    data = session.get("data", {})
    text = (update.message_text or "").strip()

    if state == "ask_name":
        if not text:
            return {"reply": "Напиши, пожалуйста, как к тебе обращаться", "state": state}
        data["client_name"] = text
        db["botsession"].update_one({"_id": session["_id"]}, {"$set": {"state": "ask_phone", "data": data}})
        return {"reply": "Оставь телефон или @username для связи", "state": "ask_phone"}

    if state == "ask_phone":
        data["phone"] = text
        db["botsession"].update_one({"_id": session["_id"]}, {"$set": {"state": "ask_date", "data": data}})
        return {"reply": "Когда тебе удобно? Укажи дату (например, 2025-11-20)", "state": "ask_date"}

    if state == "ask_date":
        data["preferred_date"] = text
        db["botsession"].update_one({"_id": session["_id"]}, {"$set": {"state": "ask_time", "data": data}})
        return {"reply": "А во сколько примерно?", "state": "ask_time"}

    if state == "ask_time":
        data["preferred_time"] = text
        db["botsession"].update_one({"_id": session["_id"]}, {"$set": {"state": "ask_note", "data": data}})
        return {"reply": "Добавь пожелания по стилю/размеру (или напиши — нет)", "state": "ask_note"}

    if state == "ask_note":
        data["note"] = text
        data["source"] = "bot"
        data["telegram_user_id"] = user_id
        app_id = create_document("appointment", data)
        db["botsession"].update_one({"_id": session["_id"]}, {"$set": {"state": "complete"}})
        return {"reply": "Готово! Я записал заявку №" + app_id + ". Мы свяжемся с тобой.", "state": "complete"}

    return {"reply": "Напиши любое сообщение, чтобы начать запись", "state": "ask_name"}


# Simple JSON export for backups
@app.get("/backup/export")
def export_backup(password: str):
    require_admin(password)
    collections = ["tattooservice", "portfolioitem", "appointment", "botsession"]
    dump = {}
    for col in collections:
        docs = list(db[col].find({}))
        for d in docs:
            d["id"] = str(d.pop("_id"))
        dump[col] = docs
    return dump


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

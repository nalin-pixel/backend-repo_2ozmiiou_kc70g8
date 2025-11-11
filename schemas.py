"""
Database Schemas for Tattoo Artist App

Each Pydantic model corresponds to a MongoDB collection.
Collection name is the lowercase class name.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TattooService(BaseModel):
    title: str = Field(..., description="Service name, e.g., 'Small Blackwork' ")
    description: Optional[str] = Field(None, description="Short description")
    price_from: Optional[float] = Field(None, ge=0, description="Starting price")
    duration_min: Optional[int] = Field(None, ge=0, description="Estimated duration in minutes")
    is_active: bool = Field(True, description="Visible for clients")


class PortfolioItem(BaseModel):
    title: str = Field(..., description="Work title")
    image_url: str = Field(..., description="Public image URL")
    style: Optional[str] = Field(None, description="Tattoo style tag")
    description: Optional[str] = Field(None, description="Optional caption")
    featured: bool = Field(False, description="Show on homepage hero")


class Appointment(BaseModel):
    client_name: str = Field(..., description="Client full name")
    phone: Optional[str] = Field(None, description="Phone or Telegram @username")
    telegram_user_id: Optional[int] = Field(None, description="Telegram numeric user id if booked via bot")
    service_id: Optional[str] = Field(None, description="Related service id as string")
    preferred_date: Optional[str] = Field(None, description="Preferred date string (YYYY-MM-DD or free form)")
    preferred_time: Optional[str] = Field(None, description="Preferred time string")
    note: Optional[str] = Field(None, description="Additional notes / style preferences")
    status: str = Field("new", description="new | confirmed | done | canceled")
    source: str = Field("site", description="site | bot")


class BotSession(BaseModel):
    telegram_user_id: int = Field(..., description="Telegram user id")
    state: str = Field("start", description="start|ask_name|ask_phone|ask_date|ask_time|ask_note|complete")
    data: dict = Field(default_factory=dict)
    last_update: Optional[datetime] = None


class AdminLogin(BaseModel):
    password: str


# Note: The Flames database viewer will automatically use these schemas if /schema endpoint is exposed.

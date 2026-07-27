"""SQLite models.

Data model inspired by googlarz/fashion-skill (CC BY 4.0).
"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Profile(Base):
    __tablename__ = "profile"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    body_json: Mapped[str] = mapped_column(Text, default="{}")
    color_season: Mapped[str | None]
    color_undertone: Mapped[str | None]
    palette_json: Mapped[str] = mapped_column(Text, default="[]")
    style_keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    avoids_json: Mapped[str] = mapped_column(Text, default="[]")
    preferred_colors_json: Mapped[str] = mapped_column(Text, default="[]")
    preferred_styles_json: Mapped[str] = mapped_column(Text, default="[]")
    brand_sizes_json: Mapped[str] = mapped_column(Text, default="{}")
    city: Mapped[str | None]
    climate: Mapped[str | None]
    occasions_json: Mapped[str] = mapped_column(Text, default="[]")
    budget_top_cents: Mapped[int | None]
    budget_bottom_cents: Mapped[int | None]
    budget_outerwear_cents: Mapped[int | None]
    learned_from_feedback_json: Mapped[str] = mapped_column(Text, default="[]")
    formulas_json: Mapped[str] = mapped_column(Text, default="[]")
    last_profile_refresh: Mapped[datetime | None] = mapped_column(DateTime)
    taste_memo: Mapped[str] = mapped_column(Text, default="")
    taste_memo_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    feedback_since_refresh: Mapped[int] = mapped_column(Integer, default=0)


class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"
    __table_args__ = (
        Index("ix_wardrobe_user_category", "user_id", "category"),
        Index("ix_wardrobe_user_status", "user_id", "status"),
        Index("ix_wardrobe_user_confirmed", "user_id", "confirmed_by_user"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String)
    name: Mapped[str | None]
    category: Mapped[str | None]
    primary_color: Mapped[str | None]
    secondary_color: Mapped[str | None]
    material: Mapped[str | None]
    fit: Mapped[str | None]
    formality: Mapped[str | None]
    style_json: Mapped[str] = mapped_column(Text, default="[]")
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    seasons_json: Mapped[str] = mapped_column(Text, default="[]")
    occasions_json: Mapped[str] = mapped_column(Text, default="[]")
    versatility: Mapped[float | None] = mapped_column(Float)
    brand: Mapped[str | None]
    size: Mapped[str | None]
    image_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_raw_response: Mapped[str | None] = mapped_column(Text)
    duplicate_of: Mapped[str | None]
    duplicate_confidence: Mapped[float | None] = mapped_column(Float)
    confirmed_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class OutfitHistory(Base):
    __tablename__ = "outfit_history"
    __table_args__ = (
        Index("ix_history_user_date", "user_id", "date"),
        Index("ix_history_user_action", "user_id", "action"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String)
    date: Mapped[date] = mapped_column(Date, default=date.today)
    occasion: Mapped[str | None]
    mood: Mapped[str | None]
    weather_summary: Mapped[str | None]
    temp: Mapped[float | None] = mapped_column(Float)
    outfit_name: Mapped[str | None]
    item_ids_json: Mapped[str] = mapped_column(Text)
    pick_mode: Mapped[str] = mapped_column(String)
    reason: Mapped[str | None] = mapped_column(Text)
    collage_path: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String, default="shown")
    user_rating: Mapped[int | None]
    wore_it: Mapped[bool] = mapped_column(Boolean, default=False)


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        Index("ix_feedback_user_date", "user_id", "date"),
        Index("ix_feedback_user_occasion_date", "user_id", "occasion_type", "date"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String)
    date: Mapped[date] = mapped_column(Date, default=date.today)
    items_worn_json: Mapped[str] = mapped_column(Text, default="[]")
    occasion: Mapped[str | None]
    occasion_type: Mapped[str | None]
    sentiment: Mapped[str | None]
    compliments_json: Mapped[str] = mapped_column(Text, default="[]")
    didnt_work: Mapped[str | None] = mapped_column(Text)
    learnings: Mapped[str | None] = mapped_column(Text)

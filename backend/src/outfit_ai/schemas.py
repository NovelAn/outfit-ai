from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClothingAttributes(BaseModel):
    name: str
    category: str
    primary_color: str
    secondary_color: str | None = None
    material: str | None = None
    fit: str | None = None
    formality: str | None = None
    styles: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    seasons: list[str] = Field(default_factory=list)
    occasions: list[str] = Field(default_factory=list)
    versatility: float | None = Field(None, ge=0, le=1)


class ProposedLook(BaseModel):
    tier: Literal["safe", "fresh", "stretch"]
    item_ids: list[str] = Field(min_length=1)
    reason: str
    weather_fit: str
    occasion_fit: str


class WardrobePatch(BaseModel):
    name: str | None = None
    category: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    material: str | None = None
    fit: str | None = None
    formality: str | None = None
    styles: list[str] | None = None
    tags: list[str] | None = None
    seasons: list[str] | None = None
    occasions: list[str] | None = None
    versatility: float | None = Field(None, ge=0, le=1)
    brand: str | None = None
    size: str | None = None
    confirmed_by_user: bool | None = None


class WardrobeItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str | None
    category: str | None
    primary_color: str | None
    image_url: str
    status: str
    attempt_count: int
    confirmed_by_user: bool
    attributes: dict | None = None


class ProfileIn(BaseModel):
    body: dict = Field(default_factory=dict)
    color_season: str | None = None
    color_undertone: str | None = None
    palette: list[str] = Field(default_factory=list)
    style_keywords: list[str] = Field(default_factory=list)
    avoids: list[str] = Field(default_factory=list)
    preferred_colors: list[str] = Field(default_factory=list)
    preferred_styles: list[str] = Field(default_factory=list)
    brand_sizes: dict = Field(default_factory=dict)
    city: str | None = None
    climate: str | None = None
    occasions: list[str] = Field(default_factory=list)
    budget_top_cents: int | None = Field(None, ge=0)
    budget_bottom_cents: int | None = Field(None, ge=0)
    budget_outerwear_cents: int | None = Field(None, ge=0)
    learned_from_feedback: list[str] = Field(default_factory=list)
    formulas: list[str] = Field(default_factory=list)
    taste_memo: str = ""


class ProfileOut(ProfileIn):
    user_id: str
    taste_memo_updated_at: datetime | None = None
    feedback_since_refresh: int = 0


class RecommendRequest(BaseModel):
    occasion: str = "日常"
    mood: str | None = None
    city: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    locked_item_ids: list[str] = Field(default_factory=list)


class StyleDnaDraftRequest(BaseModel):
    samples: list[str] = Field(default_factory=list, max_length=6)
    text: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def require_input(self):
        if not self.samples and not self.text.strip():
            raise ValueError("至少提供文字描述或一张参考图")
        return self


class FeedbackIn(BaseModel):
    history_id: str | None = None
    items_worn: list[str] = Field(default_factory=list)
    action: Literal["shown", "saved", "skipped", "worn"]
    occasion: str | None = None
    occasion_type: str | None = None
    sentiment: str | None = None
    compliments: list[str] = Field(default_factory=list)
    didnt_work: str | None = None
    learnings: str | None = None


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    date: date
    item_ids: list[str]
    pick_mode: str
    occasion: str | None
    mood: str | None
    reason: str | None
    action: str
    wore_it: bool

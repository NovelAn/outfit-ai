from datetime import date, datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel, Field, field_validator, model_validator

OutfitHistoryAction: TypeAlias = Literal[
    "shown", "saved", "skipped", "worn", "prepared"
]


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

    @field_validator("versatility", mode="before")
    @classmethod
    def normalize_semantic_versatility(cls, value):
        if isinstance(value, bool):
            raise ValueError("versatility 必须是数值")
        if isinstance(value, str):
            normalized = value.strip().lower()
            return {
                "高": 0.85,
                "high": 0.85,
                "中": 0.5,
                "medium": 0.5,
                "低": 0.25,
                "low": 0.25,
            }.get(normalized, value)
        return value


class StyleReferenceAnalysis(BaseModel):
    style_keywords: list[str] = Field(default_factory=list)
    palette: list[str] = Field(default_factory=list)
    silhouettes: list[str] = Field(default_factory=list)
    layering: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    seasons: list[str] = Field(default_factory=list)
    scenes: list[str] = Field(default_factory=list)
    notable_elements: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_visible_style_evidence(self):
        if not any(
            (
                self.style_keywords,
                self.palette,
                self.silhouettes,
                self.layering,
                self.materials,
                self.seasons,
                self.scenes,
                self.notable_elements,
            )
        ):
            raise ValueError("参考 Look 分析不能全部为空")
        return self


class StyleDnaMerge(BaseModel):
    style_keywords: list[str] = Field(default_factory=list)
    recent_style_signals: list[str] = Field(default_factory=list)
    palette: list[str] = Field(default_factory=list)
    preferred_colors: list[str] = Field(default_factory=list)
    preferred_styles: list[str] = Field(default_factory=list)
    avoids: list[str] = Field(default_factory=list)
    taste_memo: str = ""


class ProposedLook(BaseModel):
    tier: Literal["safe", "fresh", "stretch"]
    item_ids: list[str] = Field(min_length=3, max_length=6)
    reason: str
    weather_fit: str
    occasion_fit: str

    @field_validator("item_ids")
    @classmethod
    def require_unique_items(cls, item_ids: list[str]) -> list[str]:
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("单套推荐不能包含重复单品")
        return item_ids


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
    recent_style_signals: list[str] = Field(default_factory=list)
    style_tag_preferences: dict = Field(
        default_factory=lambda: {"pinned": [], "hidden": [], "aliases": {}}
    )
    last_location: dict | None = None
    formulas: list[str] = Field(default_factory=list)
    taste_memo: str = ""


class ProfileOut(ProfileIn):
    user_id: str
    taste_memo_updated_at: datetime | None = None
    feedback_since_refresh: int = 0


class RecommendRequest(BaseModel):
    occasion: str = "日常"
    scene: str | None = Field(None, max_length=40)
    mood: str | None = None
    season: Literal["spring", "summer", "autumn", "winter", "spring_autumn"] | None = None
    style_note: str | None = Field(None, max_length=500)
    reference_ids: list[str] = Field(default_factory=list, max_length=6)
    city: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    local_date: date | None = None
    locked_item_ids: list[str] = Field(default_factory=list)
    force_refresh: bool = False
    refresh_tier: Literal["safe", "fresh", "stretch"] | None = None

    @model_validator(mode="after")
    def require_force_refresh_for_tier(self):
        if self.refresh_tier and not self.force_refresh:
            raise ValueError("refresh_tier 只能与 force_refresh=true 一起使用")
        return self


class InspirationRequest(BaseModel):
    reference_ids: list[str] = Field(default_factory=list, max_length=6)
    style_note: str | None = Field(None, max_length=500)
    season: Literal["spring", "summer", "autumn", "winter", "spring_autumn"] | None = None
    scene: str = Field(default="日常", min_length=1, max_length=40)


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
    action: Literal["shown", "saved", "skipped", "worn"] | None = None
    rating: int | None = Field(None, ge=1, le=5)
    occasion: str | None = None
    occasion_type: str | None = None
    sentiment: str | None = None
    compliments: list[str] = Field(default_factory=list)
    didnt_work: str | None = None
    learnings: str | None = None

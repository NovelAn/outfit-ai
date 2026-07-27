import json
import threading
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import select, update

from ..config import settings
from ..db import SessionLocal
from ..models import Feedback, Profile, WardrobeItem
from ..schemas import ProfileIn
from .llm import LLMResponseError, chat_multimodal, generate_json
from .prompt_builder import style_dna_messages

FEEDBACK_BATCH_SIZE = 8
# ponytail: process-local lock; use a durable queue/DB lease when multiple workers are needed.
_REFRESH_LOCK = threading.Lock()

_STYLE_DNA_TOOL = {
    "type": "function",
    "function": {
        "name": "save_style_dna",
        "description": "保存可编辑 Style DNA 与初版品味备忘录",
        "parameters": ProfileIn.model_json_schema(),
    },
}


class TasteMemoResult(BaseModel):
    taste_memo: str = Field(min_length=1)


def _json_list(value: str | None) -> list:
    return json.loads(value or "[]")


def seed(samples: list[str], text: str) -> ProfileIn:
    response = chat_multimodal(
        style_dna_messages(samples, text),
        tools=[_STYLE_DNA_TOOL],
        tool_choice={"type": "function", "function": {"name": "save_style_dna"}},
    )
    try:
        arguments = response.choices[0].message.tool_calls[0].function.arguments
        return ProfileIn.model_validate_json(arguments)
    except (AttributeError, IndexError, TypeError, ValueError) as exc:
        raise LLMResponseError("MiniMax 未返回有效的 Style DNA 工具调用") from exc


def _restore_claim(user_id: str, claimed_batch: int) -> None:
    if not claimed_batch:
        return
    with SessionLocal() as db:
        db.execute(
            update(Profile)
            .where(Profile.user_id == user_id)
            .values(
                feedback_since_refresh=(
                    Profile.feedback_since_refresh + claimed_batch
                )
            )
        )
        db.commit()


def refresh(
    user_id: str = settings.user_id,
    claimed_batch: int = 0,
) -> None:
    with _REFRESH_LOCK:
        try:
            with SessionLocal() as db:
                profile = db.get(Profile, user_id)
                if not profile:
                    return
                feedback = list(
                    db.scalars(
                        select(Feedback)
                        .where(Feedback.user_id == user_id)
                        .order_by(Feedback.date.desc(), Feedback.id.desc())
                        .limit(FEEDBACK_BATCH_SIZE)
                    )
                )
                item_ids = {
                    item_id
                    for row in feedback
                    for item_id in _json_list(row.items_worn_json)
                }
                wardrobe_items = list(
                    db.scalars(
                        select(WardrobeItem).where(
                            WardrobeItem.user_id == user_id,
                            WardrobeItem.id.in_(item_ids),
                        )
                    )
                )
                result = TasteMemoResult.model_validate(
                    generate_json(
                        "根据真实反馈更新品味备忘录。保留仍有效信息，不因单次反馈过度推断。",
                        json.dumps(
                            {
                                "old_memo": profile.taste_memo,
                                "feedback": [
                                    {
                                        "id": row.id,
                                        "date": row.date.isoformat(),
                                        "items_worn": _json_list(row.items_worn_json),
                                        "occasion": row.occasion,
                                        "occasion_type": row.occasion_type,
                                        "sentiment": row.sentiment,
                                        "compliments": _json_list(row.compliments_json),
                                        "didnt_work": row.didnt_work,
                                        "learnings": row.learnings,
                                    }
                                    for row in feedback
                                ],
                                "wardrobe_items": [
                                    {
                                        "id": item.id,
                                        "name": item.name,
                                        "category": item.category,
                                        "primary_color": item.primary_color,
                                        "secondary_color": item.secondary_color,
                                        "material": item.material,
                                        "fit": item.fit,
                                        "formality": item.formality,
                                        "styles": _json_list(item.style_json),
                                        "tags": _json_list(item.tags_json),
                                        "seasons": _json_list(item.seasons_json),
                                        "occasions": _json_list(item.occasions_json),
                                        "versatility": item.versatility,
                                        "brand": item.brand,
                                        "size": item.size,
                                    }
                                    for item in wardrobe_items
                                ],
                            },
                            ensure_ascii=False,
                        ),
                        '{"taste_memo":"更新后的自然语言档案"}',
                    )
                )
                profile.taste_memo = result.taste_memo
                profile.taste_memo_updated_at = datetime.now()
                db.commit()
        except Exception:
            _restore_claim(user_id, claimed_batch)
            raise

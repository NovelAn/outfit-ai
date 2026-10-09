import json
import threading
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import literal_column, select, update

from ..config import settings
from ..db import SessionLocal
from ..models import Feedback, FeedbackEvent, Profile, WardrobeItem
from ..schemas import ProfileIn
from .llm import LLMResponseError, chat_multimodal, generate_json
from .prompt_builder import style_dna_messages

FEEDBACK_BATCH_SIZE = 4
# ponytail: process-local lock + additive revision/update timestamps; multiple workers
# would still need a durable claim protocol beyond the current local SQLite process.
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
    learned_this_round: str = ""


def _json_list(value: str | None) -> list:
    try:
        decoded = json.loads(value or "[]")
    except (TypeError, ValueError):
        return []
    return decoded if isinstance(decoded, list) else []


def _positive_signals(row: FeedbackEvent) -> list:
    return _json_list(row.positive_signals_json)


def _backfill_legacy_feedback_events(db, user_id: str) -> None:
    """Materialize one event per legacy feedback row before event-based refresh.

    Rows written before the event ledger migration only have the current final
    fact. They still represent one learnable signal, so preserve them instead of
    failing the first refresh after upgrade.
    """
    legacy_rows = db.scalars(
        select(Feedback)
        .outerjoin(FeedbackEvent, FeedbackEvent.feedback_id == Feedback.id)
        .where(Feedback.user_id == user_id, FeedbackEvent.id.is_(None))
        .distinct()
    ).all()
    for row in legacy_rows:
        db.add(
            FeedbackEvent(
                id=f"legacy-{row.id}",
                feedback_id=row.id,
                user_id=row.user_id,
                history_id=row.history_id,
                date=row.date,
                event_at=row.updated_at or row.created_at or datetime.now(),
                items_worn_json=row.items_worn_json,
                action=row.action,
                rating=row.rating,
                occasion=row.occasion,
                occasion_type=row.occasion_type,
                sentiment=row.sentiment,
                positive_signals_json=(
                    row.positive_signals_json
                    if _json_list(row.positive_signals_json)
                    else row.compliments_json
                ),
                negative_signals_json=row.negative_signals_json,
                adjustment_signals_json=row.adjustment_signals_json,
                didnt_work=row.didnt_work,
                learnings=row.learnings,
                wore_it=row.wore_it,
            )
        )
    if legacy_rows:
        db.commit()


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


def refresh(
    user_id: str = settings.user_id,
    force: bool = False,
) -> None:
    with _REFRESH_LOCK:
        while True:
            with SessionLocal() as db:
                profile = db.get(Profile, user_id)
                if not profile:
                    return
                batch_size = profile.feedback_since_refresh
                memo_revision = profile.taste_memo_revision or 0
                if batch_size == 0 or (batch_size < FEEDBACK_BATCH_SIZE and not force):
                    return
                db.execute(
                    update(Profile)
                    .where(Profile.user_id == user_id)
                    .values(
                        taste_memo_refresh_status="running",
                        taste_memo_refresh_error=None,
                    )
                )
                db.commit()
                _backfill_legacy_feedback_events(db, user_id)
                feedback_events = list(
                    db.scalars(
                        select(FeedbackEvent)
                        .where(FeedbackEvent.user_id == user_id)
                        .order_by(
                            FeedbackEvent.event_at.desc(),
                            literal_column("feedback_events.rowid").desc(),
                        )
                        .limit(batch_size)
                    )
                )
                if len(feedback_events) != batch_size:
                    error = RuntimeError("反馈计数与记录不一致")
                    db.execute(
                        update(Profile)
                        .where(
                            Profile.user_id == user_id,
                            Profile.taste_memo_revision == memo_revision,
                        )
                        .values(
                            taste_memo_refresh_status="failed",
                            taste_memo_refresh_error=str(error),
                        )
                    )
                    db.commit()
                    raise error
                item_ids = {
                    item_id
                    for row in feedback_events
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
                context = {
                    "old_memo": profile.taste_memo,
                    "feedback": [
                        {
                            "id": row.id,
                            "feedback_id": row.feedback_id,
                            "history_id": row.history_id,
                            "date": row.date.isoformat(),
                            "created_at": row.event_at.isoformat(),
                            "updated_at": row.event_at.isoformat(),
                            "items_worn": _json_list(row.items_worn_json),
                            "action": row.action,
                            "rating": row.rating,
                            "occasion": row.occasion,
                            "occasion_type": row.occasion_type,
                            "sentiment": row.sentiment,
                            "positive_signals": _positive_signals(row),
                            "negative_signals": _json_list(row.negative_signals_json),
                            "adjustment_signals": _json_list(
                                row.adjustment_signals_json
                            ),
                            "didnt_work": row.didnt_work,
                            "learnings": row.learnings,
                        }
                        for row in feedback_events
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
                }
            try:
                result = TasteMemoResult.model_validate(
                    generate_json(
                        "根据真实反馈更新品味备忘录。保留仍有效信息，不因单次反馈过度推断。"
                        "同时用一句话说明本轮依据反馈学到的变化。",
                        json.dumps(context, ensure_ascii=False),
                        '{"taste_memo":"更新后的自然语言档案",'
                        '"learned_this_round":"本轮学到的变化"}',
                    )
                )
            except Exception as exc:
                with SessionLocal() as failed_db:
                    failed_db.execute(
                        update(Profile)
                        .where(
                            Profile.user_id == user_id,
                            Profile.taste_memo_revision == memo_revision,
                        )
                        .values(
                            taste_memo_refresh_status="failed",
                            taste_memo_refresh_error=str(exc)[:500],
                        )
                    )
                    failed_db.commit()
                raise
            with SessionLocal() as db:
                updated = db.execute(
                    update(Profile)
                    .where(
                        Profile.user_id == user_id,
                        Profile.taste_memo_revision == memo_revision,
                        Profile.feedback_since_refresh >= batch_size,
                    )
                    .values(
                        taste_memo=result.taste_memo,
                        taste_memo_updated_at=datetime.now(),
                        taste_memo_last_change=result.learned_this_round,
                        taste_memo_source_feedback_ids_json=json.dumps(
                            [row.feedback_id for row in feedback_events], ensure_ascii=False
                        ),
                        taste_memo_source_event_ids_json=json.dumps(
                            [row.id for row in feedback_events], ensure_ascii=False
                        ),
                        taste_memo_refresh_status="idle",
                        taste_memo_refresh_error=None,
                        feedback_since_refresh=(
                            Profile.feedback_since_refresh - batch_size
                        ),
                    )
                ).rowcount
                if updated != 1:
                    db.rollback()
                    return
                db.commit()
            force = False

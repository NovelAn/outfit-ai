import json
from datetime import datetime

from sqlalchemy import select

from ..config import settings
from ..db import SessionLocal
from ..models import Feedback, Profile
from .llm import generate_json


def seed(profile_data: dict) -> str:
    result = generate_json(
        "你是个人风格档案编辑，只总结用户明确表达的偏好，不自行杜撰。",
        json.dumps(profile_data, ensure_ascii=False),
        '{"taste_memo":"自然语言品味备忘录"}',
    )
    return str(result["taste_memo"])


def refresh(user_id: str = settings.user_id) -> None:
    with SessionLocal() as db:
        profile = db.get(Profile, user_id)
        if not profile:
            return
        feedback = list(
            db.scalars(
                select(Feedback)
                .where(Feedback.user_id == user_id)
                .order_by(Feedback.date.desc())
                .limit(20)
            )
        )
        result = generate_json(
            "根据真实反馈更新品味备忘录。保留仍有效信息，不因单次反馈过度推断。",
            json.dumps(
                {
                    "old_memo": profile.taste_memo,
                    "feedback": [
                        {
                            "sentiment": row.sentiment,
                            "didnt_work": row.didnt_work,
                            "learnings": row.learnings,
                        }
                        for row in feedback
                    ],
                },
                ensure_ascii=False,
            ),
            '{"taste_memo":"更新后的自然语言档案"}',
        )
        profile.taste_memo = str(result["taste_memo"])
        profile.taste_memo_updated_at = datetime.now()
        profile.feedback_since_refresh = 0
        db.commit()

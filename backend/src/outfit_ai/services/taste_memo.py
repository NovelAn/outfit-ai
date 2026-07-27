import json
from datetime import datetime

from sqlalchemy import select

from ..config import settings
from ..db import SessionLocal
from ..models import Feedback, Profile
from ..schemas import ProfileIn
from .llm import LLMResponseError, chat_multimodal, generate_json
from .prompt_builder import style_dna_messages

_STYLE_DNA_TOOL = {
    "type": "function",
    "function": {
        "name": "save_style_dna",
        "description": "保存可编辑 Style DNA 与初版品味备忘录",
        "parameters": ProfileIn.model_json_schema(),
    },
}


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

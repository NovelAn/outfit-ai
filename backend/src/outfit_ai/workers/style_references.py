import json

from sqlalchemy import update

from ..config import settings
from ..db import SessionLocal
from ..models import Profile, StyleReference
from ..schemas import StyleDnaMerge, StyleReferenceAnalysis
from ..services.style_references import merge_style_dna
from ..services.vision import analyze_reference


def process_reference(reference_id: str) -> None:
    with SessionLocal() as db:
        claimed = db.scalar(
            update(StyleReference)
            .where(
                StyleReference.id == reference_id,
                StyleReference.status == "pending",
            )
            .values(
                status="analyzing",
                attempt_count=StyleReference.attempt_count + 1,
            )
            .returning(StyleReference.id)
        )
        db.commit()
        if not claimed:
            return
        reference = db.get(StyleReference, reference_id)
        if not reference:
            return
        try:
            if reference.analysis_json:
                analysis = StyleReferenceAnalysis.model_validate_json(
                    reference.analysis_json
                )
            else:
                analysis, raw = analyze_reference(reference.image_path)
                reference.analysis_json = analysis.model_dump_json()
                reference.ai_raw_response = raw
            profile = db.get(Profile, settings.user_id)
            merged = StyleDnaMerge.model_validate(merge_style_dna(profile, analysis))
            if not profile:
                profile = Profile(user_id=settings.user_id)
                db.add(profile)
            for field in (
                "style_keywords",
                "palette",
                "preferred_colors",
                "preferred_styles",
                "avoids",
            ):
                setattr(
                    profile,
                    f"{field}_json",
                    json.dumps(getattr(merged, field), ensure_ascii=False),
                )
            profile.taste_memo = merged.taste_memo
            reference.status = "ready"
        except Exception as exc:
            reference.ai_raw_response = str(exc)[:500]
            reference.status = "failed"
        db.commit()

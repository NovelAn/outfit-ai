from pathlib import Path

from sqlalchemy import func, select

from outfit_ai.config import settings
from outfit_ai.db import Base, SessionLocal, engine
from outfit_ai.models import WardrobeItem


def test_global_runtime_probe_writes_state_for_isolation_check() -> None:
    Base.metadata.create_all(engine)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        db.add(
            WardrobeItem(
                id="isolation-probe",
                user_id="local",
                image_path=str(Path(settings.upload_dir) / "isolation-probe.jpg"),
            )
        )
        db.commit()
    Path(settings.upload_dir, "isolation-probe.jpg").write_bytes(b"probe")


def test_global_runtime_starts_clean_for_each_test() -> None:
    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(WardrobeItem))

    assert count == 0
    assert not Path(settings.upload_dir, "isolation-probe.jpg").exists()

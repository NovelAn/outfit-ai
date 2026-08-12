import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

_TEST_DATA = TemporaryDirectory(prefix="outfit-ai-tests-")
_TEST_ROOT = Path(_TEST_DATA.name)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_ROOT / 'outfit_ai.db'}"
os.environ["UPLOAD_DIR"] = str(_TEST_ROOT / "uploads")


@pytest.fixture(autouse=True)
def isolate_global_runtime() -> None:
    from outfit_ai import models  # noqa: F401
    from outfit_ai.db import Base, engine

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    shutil.rmtree(_TEST_ROOT / "uploads", ignore_errors=True)
    (_TEST_ROOT / "uploads").mkdir()
    yield
    Base.metadata.drop_all(engine)
    shutil.rmtree(_TEST_ROOT / "uploads", ignore_errors=True)

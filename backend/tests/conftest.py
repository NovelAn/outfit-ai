import os
from pathlib import Path
from tempfile import TemporaryDirectory

_TEST_DATA = TemporaryDirectory(prefix="outfit-ai-tests-")
_TEST_ROOT = Path(_TEST_DATA.name)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_ROOT / 'outfit_ai.db'}"
os.environ["UPLOAD_DIR"] = str(_TEST_ROOT / "uploads")

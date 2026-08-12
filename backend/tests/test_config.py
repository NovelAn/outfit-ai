from pathlib import Path

from outfit_ai.config import Settings


def test_default_runtime_data_lives_in_stable_user_directory(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("UPLOAD_DIR", raising=False)

    configured = Settings(_env_file=None)
    data_root = Path.home() / ".outfit-ai"

    assert configured.database_url == f"sqlite:///{data_root / 'outfit_ai.db'}"
    assert configured.upload_dir == str(data_root / "uploads")


def test_runtime_paths_expand_user_directory(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///~/.outfit-ai/custom.db")
    monkeypatch.setenv("UPLOAD_DIR", "~/.outfit-ai/custom-uploads")

    configured = Settings(_env_file=None)

    assert configured.database_url == f"sqlite:///{Path.home() / '.outfit-ai/custom.db'}"
    assert configured.upload_dir == str(Path.home() / ".outfit-ai/custom-uploads")

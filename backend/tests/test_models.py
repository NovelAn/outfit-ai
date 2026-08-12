from sqlalchemy import create_engine, inspect, text

from outfit_ai import models  # noqa: F401
from outfit_ai.db import Base, _add_outfit_history_context_column


def test_schema_has_five_tables_and_no_weight_table() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    assert set(inspect(engine).get_table_names()) == {
        "feedback",
        "outfit_history",
        "profile",
        "style_references",
        "wardrobe_items",
    }
    assert {"taste_memo", "feedback_since_refresh"} <= {
        column["name"] for column in inspect(engine).get_columns("profile")
    }
    assert "context_json" in {
        column["name"] for column in inspect(engine).get_columns("outfit_history")
    }


def test_legacy_outfit_history_gains_context_column_once() -> None:
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE outfit_history ("
                "id TEXT PRIMARY KEY, item_ids_json TEXT NOT NULL)"
            )
        )
        connection.execute(
            text("INSERT INTO outfit_history (id, item_ids_json) VALUES ('legacy', '[]')")
        )

    _add_outfit_history_context_column(engine)
    _add_outfit_history_context_column(engine)

    assert [column["name"] for column in inspect(engine).get_columns("outfit_history")].count(
        "context_json"
    ) == 1
    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT item_ids_json FROM outfit_history WHERE id = 'legacy'")
        ) == "[]"

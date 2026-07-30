from sqlalchemy import create_engine, inspect

from outfit_ai import models  # noqa: F401
from outfit_ai.db import Base


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

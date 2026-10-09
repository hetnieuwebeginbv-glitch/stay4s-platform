import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("training", ROOT / "generate_stay4s_training_data_v1.py")
training = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(training)

def test_exact_record_count_and_schema():
    rows = training.build_records()
    assert len(rows) == 5000
    assert all(set(row) == {"messages"} for row in rows)
    assert all(len(row["messages"]) == 2 for row in rows)
    assert all([m["role"] for m in row["messages"]] == ["user", "assistant"] for row in rows)
    assert all(all(isinstance(m["content"], str) and m["content"] for m in row["messages"]) for row in rows)

def test_generator_is_deterministic():
    assert training.build_records(123) == training.build_records(123)
    assert training.build_records(123) != training.build_records(124)

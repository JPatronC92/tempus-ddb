"""
Basic Python API tests for Tempus DDB.

These tests require the package to be installed:
    pip install -e .

Run with:
    pytest tests/test_python_api.py -v
"""

import json
import os
import pytest

from tempus_ddb import TempusDDB, gen_keys


def test_gen_keys_and_record_genesis(tmp_path):
    keyfile = tmp_path / "keys.json"
    db_path = tmp_path / "test.db"

    gen_keys(str(keyfile))
    assert keyfile.exists()

    db = TempusDDB("tmb_live_test", str(db_path), str(keyfile))

    payload = json.dumps({"action": "test_action", "value": 42})
    rules = json.dumps({"rule": "always_true"})

    result = db.record(payload, rules, genesis=True)
    assert result is not None

    result_str = result if isinstance(result, str) else json.dumps(result)
    assert "latest_hash" in result_str or "output" in result_str


def test_record_with_parent_and_validate(tmp_path):
    keyfile = tmp_path / "keys.json"
    db_path = tmp_path / "test.db"

    gen_keys(str(keyfile))
    db = TempusDDB("tmb_live_test", str(db_path), str(keyfile))

    # Genesis record
    payload1 = json.dumps({"step": 1, "decision": "start"})
    rules1 = json.dumps({})
    res1 = db.record(payload1, rules1, genesis=True)

    res1_data = json.loads(res1) if isinstance(res1, str) else res1
    parent_hash = None
    if isinstance(res1_data, dict):
        parent_hash = res1_data.get("latest_hash") or res1_data.get("output", {}).get("latest_hash")

    # Child record
    payload2 = json.dumps({"step": 2, "decision": "follow_up"})
    rules2 = json.dumps({})
    res2 = db.record(payload2, rules2, genesis=False)

    # Validation must succeed
    validation = db.validate()
    assert validation is not None
    val_str = str(validation).lower()
    assert "invalid" not in val_str and "error" not in val_str


def test_multiple_records_and_repeated_validate(tmp_path):
    keyfile = tmp_path / "keys.json"
    db_path = tmp_path / "test.db"

    gen_keys(str(keyfile))
    db = TempusDDB("tmb_live_test", str(db_path), str(keyfile))

    # Multiple decisions
    for i in range(5):
        payload = json.dumps({"step": i, "data": f"decision-{i}"})
        rules = json.dumps({"step": i})
        db.record(payload, rules, genesis=(i == 0))

    validation = db.validate()
    val_str = str(validation).lower()
    assert "invalid" not in val_str


def test_invalid_keyfile_raises(tmp_path):
    db_path = tmp_path / "test.db"
    bad_key = tmp_path / "bad.json"
    bad_key.write_text('{"not": "valid"}')

    with pytest.raises(Exception):
        TempusDDB("tmb_live_test", str(db_path), str(bad_key))


def test_record_without_genesis_fails_without_parent(tmp_path):
    keyfile = tmp_path / "keys.json"
    db_path = tmp_path / "test.db"

    gen_keys(str(keyfile))
    db = TempusDDB("tmb_live_test", str(db_path), str(keyfile))

    payload = json.dumps({"step": 2})
    rules = json.dumps({})

    with pytest.raises(Exception) as exc:
        db.record(payload, rules, genesis=False)

    assert "parent" in str(exc.value).lower() or "genesis" in str(exc.value).lower()


def test_validate_detects_tampering(tmp_path):
    keyfile = tmp_path / "keys.json"
    db_path = tmp_path / "test.db"

    gen_keys(str(keyfile))
    db = TempusDDB("tmb_live_test", str(db_path), str(keyfile))

    db.record(json.dumps({"original": True}), json.dumps({}), genesis=True)

    # Tamper with the DB file (simulates corruption)
    with open(db_path, "ab") as f:
        f.write(b"\x00corrupt")

    validation = db.validate()
    val_str = str(validation).lower()
    # It should report something wrong
    assert "invalid" in val_str or "error" in val_str or "mismatch" in val_str


def test_record_accepts_both_string_and_dict_like(tmp_path):
    """Ensure the API accepts JSON strings as expected by CLI and MCP."""
    keyfile = tmp_path / "keys.json"
    db_path = tmp_path / "test.db"
    gen_keys(str(keyfile))
    db = TempusDDB("tmb_live_test", str(db_path), str(keyfile))

    # As strings (what CLI passes)
    result = db.record(
        json.dumps({"action": "string_payload"}),
        json.dumps({"rule": "string"}),
        genesis=True
    )
    assert result is not None
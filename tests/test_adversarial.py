import json
import sqlite3

import pytest
from tempus_ddb import TempusDDB, gen_keys


def test_tamper_delete_middle_record(tmp_path):
    """Test that deleting a record from the middle of the chain breaks validation."""
    keyfile = tmp_path / "keys.json"
    db_path = tmp_path / "test.db"
    gen_keys(str(keyfile))
    db = TempusDDB(str(db_path), str(keyfile))

    db.record(json.dumps({"step": 1}), "{}", genesis=True)
    db.record(json.dumps({"step": 2}), "{}", genesis=False)
    db.record(json.dumps({"step": 3}), "{}", genesis=False)

    conn = sqlite3.connect(str(db_path))
    try:
        # Get the second record
        cur = conn.cursor()
        cur.execute("SELECT id FROM decisions ORDER BY timestamp ASC LIMIT 1 OFFSET 1")
        mid_hash = cur.fetchone()[0]
        # Delete it
        conn.execute("DELETE FROM decisions WHERE id = ?", (mid_hash,))
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(Exception) as exc:
        db.validate()
    assert (
        "invalid" in str(exc.value).lower()
        or "error" in str(exc.value).lower()
        or "mismatch" in str(exc.value).lower()
        or "parent" in str(exc.value).lower()
    )


def test_tamper_modify_payload(tmp_path):
    """Test that modifying a payload after recording is detected."""
    keyfile = tmp_path / "keys.json"
    db_path = tmp_path / "test.db"
    gen_keys(str(keyfile))
    db = TempusDDB(str(db_path), str(keyfile))

    db.record(json.dumps({"amount": 100}), "{}", genesis=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "UPDATE decisions SET payload = ?", (json.dumps({"amount": 1000}),)
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(Exception) as exc:
        db.validate()
    assert (
        "invalid" in str(exc.value).lower()
        or "error" in str(exc.value).lower()
        or "mismatch" in str(exc.value).lower()
    )


def test_json_canonicalization_whitespace(tmp_path):
    """Test that whitespace in JSON doesn't change the underlying canonical payload."""
    keyfile = tmp_path / "keys.json"
    db_path = tmp_path / "test.db"
    gen_keys(str(keyfile))
    db = TempusDDB(str(db_path), str(keyfile))

    # Insert with lots of whitespace
    payload = '{   "a"  :   1 , \n "b" : 2  }'
    db.record(payload, "{}", genesis=True)

    # Should be valid
    db.validate()

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT payload FROM decisions LIMIT 1")
        stored_payload = cur.fetchone()[0]
        # It should be canonicalized by the Rust core (or at least strictly parsed)
        assert json.loads(stored_payload) == {"a": 1, "b": 2}
    finally:
        conn.close()


def test_replay_attack_prevention(tmp_path):
    """Test that inserting the exact same payload in quick succession works as distinct events."""
    keyfile = tmp_path / "keys.json"
    db_path = tmp_path / "test.db"
    gen_keys(str(keyfile))
    db = TempusDDB(str(db_path), str(keyfile))

    db.record('{"event":"login"}', "{}", genesis=True)
    db.record('{"event":"login"}', "{}", genesis=False)

    # The chain should still be valid, they should have different hashes because the parent hash differs
    val = db.validate()
    assert val is not None


def test_fork_behavior_second_genesis(tmp_path):
    """Test that attempting a second genesis fails."""
    keyfile = tmp_path / "keys.json"
    db_path = tmp_path / "test.db"
    gen_keys(str(keyfile))
    db = TempusDDB(str(db_path), str(keyfile))

    db.record('{"step":1}', "{}", genesis=True)

    with pytest.raises(Exception):
        db.record('{"step":2}', "{}", genesis=True)

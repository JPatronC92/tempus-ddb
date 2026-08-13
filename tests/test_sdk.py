import json

import tempus_ddb
from tempus_ddb import TempusDDB


def test_sdk_basic_workflow(tmp_path):
    db_path = tmp_path / "test.db"
    keys_path = tmp_path / "keys.json"

    tempus_ddb.gen_keys(str(keys_path))
    assert keys_path.exists()

    db = TempusDDB(str(db_path), str(keys_path))

    payload1 = json.dumps({"action": "buy"})
    rules1 = json.dumps({"limit": 10})
    receipt1 = db.record(payload=payload1, rules=rules1, genesis=True)
    assert "latest_hash" in receipt1

    payload2 = json.dumps({"action": "sell"})
    rules2 = json.dumps({"limit": 20})
    receipt2 = db.record(payload=payload2, rules=rules2, genesis=False)
    assert "latest_hash" in receipt2

    val_result = db.validate()
    val_str = str(val_result).lower()
    assert "invalid" not in val_str
    assert "error" not in val_str

    exported_data = json.loads(db.export())
    assert isinstance(exported_data, list)
    assert len(exported_data) == 2

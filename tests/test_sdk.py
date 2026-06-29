import pytest
import os
import json
import tempfile
from tempus_ddb import TempusDDB
import tempus_ddb

def test_sdk_basic_workflow():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        keys_path = os.path.join(tmpdir, "keys.json")

        tempus_ddb.gen_keys(keys_path)
        assert os.path.exists(keys_path)

        db = TempusDDB(db_path, keys_path)

        # Genesis
        payload1 = json.dumps({"action": "buy"})
        rules1 = json.dumps({"limit": 10})
        receipt1 = db.record(payload=payload1, rules=rules1, genesis=True)
        assert "latest_hash" in receipt1

        # Second record
        payload2 = json.dumps({"action": "sell"})
        rules2 = json.dumps({"limit": 20})
        receipt2 = db.record(payload=payload2, rules=rules2, genesis=False)
        assert "latest_hash" in receipt2

        # Validation
        val_result = db.validate()
        val_str = str(val_result).lower()
        assert "invalid" not in val_str
        assert "error" not in val_str

        # Export
        export_result = db.export()
        exported_data = json.loads(export_result)
        assert isinstance(exported_data, list)
        assert len(exported_data) == 2
        
        # Explicitly delete db instance to release SQLite file lock before tmpdir cleanup
        del db

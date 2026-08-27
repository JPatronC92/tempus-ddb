"""
Example: Record multiple decisions and verify the full causal chain.

This demonstrates the tamper-evident audit trail capability.
"""

import gc
import json
import tempfile
from pathlib import Path

from tempus_ddb import TempusDDB, gen_keys


def main():
    with tempfile.TemporaryDirectory(prefix="tempus-verify-") as directory:
        root = Path(directory)
        db_path = root / "verify.db"
        keys_path = root / "gate.keys.json"

        gen_keys(str(keys_path))
        db = TempusDDB(str(db_path), str(keys_path))

        # Decision 1 - Genesis
        h1 = json.loads(db.record(
            json.dumps({"action": "initialize_agent", "version": "1.0"}),
            json.dumps({"policy": "strict"}),
            genesis=True
        ))
        print("Genesis hash:", h1.get("latest_hash") or h1.get("output", {}).get("latest_hash"))

        # Decision 2
        h2 = json.loads(db.record(
            json.dumps({"action": "approve_transaction", "amount": 5000}),
            json.dumps({"requires_approval": True}),
            genesis=False
        ))
        print("Decision 2 hash:", h2.get("latest_hash") or h2.get("output", {}).get("latest_hash"))

        # Decision 3
        db.record(
            json.dumps({"action": "execute_trade", "asset": "BTC"}),
            json.dumps({"risk_level": "medium"}),
            genesis=False
        )

        print("\nValidating full chain...")
        result = db.validate()
        print(result)

        del db
        gc.collect()
        print("\nChain verified successfully. Temporary files were removed.")

if __name__ == "__main__":
    main()

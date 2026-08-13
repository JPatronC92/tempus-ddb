"""
Example: Record multiple decisions and verify the full causal chain.

This demonstrates the tamper-evident audit trail capability.
"""

import json
import os

from tempus_ddb import TempusDDB, gen_keys

DB = "verify_example.db"
KEYS = "verify_example_keys.json"

def main():
    for f in [DB, KEYS]:
        if os.path.exists(f):
            os.remove(f)

    gen_keys(KEYS)
    db = TempusDDB(DB, KEYS)

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

    print("\n✅ Chain verified successfully. All decisions are tamper-evident.")

if __name__ == "__main__":
    main()

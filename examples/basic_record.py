"""
Basic example: Record decisions directly with the Python API.

This matches the examples shown in the README.
Run with: python examples/basic_record.py
"""

from tempus_ddb import TempusDDB, gen_keys
import json
import os

DB_PATH = "examples_tempus.db"
KEY_PATH = "examples_keys.json"

def main():
    # Clean previous run
    for f in [DB_PATH, KEY_PATH]:
        if os.path.exists(f):
            os.remove(f)

    print("=== Generating keys ===")
    gen_keys(KEY_PATH)
    print(f"Keys saved to {KEY_PATH}")

    print("\n=== Initializing ledger ===")
    db = TempusDDB(DB_PATH, KEY_PATH)
    print(f"Ledger created at {DB_PATH}")

    print("\n=== Recording genesis decision ===")
    payload1 = json.dumps({
        "action": "approve_budget",
        "amount": 12500,
        "currency": "USD",
        "reason": "Q3 marketing campaign"
    })
    rules1 = json.dumps({
        "max_amount": 15000,
        "requires_approval": True,
        "approver_role": "finance_lead"
    })

    result1 = db.record(payload1, rules1, genesis=True)
    print("Result:", result1)

    print("\n=== Recording follow-up decision ===")
    payload2 = json.dumps({
        "action": "execute_payment",
        "vendor": "Acme Corp",
        "amount": 12500,
        "reference": "INV-2024-0891"
    })
    rules2 = json.dumps({
        "budget_id": "Q3-2024-marketing",
        "approved_by": "finance_lead"
    })

    result2 = db.record(payload2, rules2, genesis=False)
    print("Result:", result2)

    print("\n=== Validating the chain ===")
    validation = db.validate()
    print("Validation:", validation)

    print("\n✅ Example completed successfully.")
    print(f"Database: {DB_PATH}")
    print(f"Keys: {KEY_PATH}")

if __name__ == "__main__":
    main()

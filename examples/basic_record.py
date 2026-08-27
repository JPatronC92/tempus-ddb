"""
Basic example: Record decisions directly with the Python API.

This matches the examples shown in the README.
Run with: python examples/basic_record.py
"""

import gc
import json
import tempfile
from pathlib import Path

from tempus_ddb import TempusDDB, gen_keys


def main():
    with tempfile.TemporaryDirectory(prefix="tempus-basic-") as directory:
        db_path = Path(directory) / "tempus.db"
        key_path = Path(directory) / "gate.keys.json"

        print("=== Generating an ephemeral demo identity ===")
        gen_keys(str(key_path))

        print("\n=== Initializing an ephemeral ledger ===")
        db = TempusDDB(str(db_path), str(key_path))

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

        del db
        gc.collect()
        print("\nExample completed successfully; temporary files were removed.")

if __name__ == "__main__":
    main()

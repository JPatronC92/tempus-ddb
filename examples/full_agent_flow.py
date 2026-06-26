"""
End-to-end example simulating an autonomous agent using Tempus DDB.

This shows a realistic flow an agent might follow for high-stakes decisions.
"""

import json
import time
from tempus_ddb import TempusDDB, gen_keys
import os

DB = "agent_flow.db"
KEYS = "agent_flow_keys.json"

def agent_decide(db, action, details, rules):
    """Simulate agent making a decision and recording it."""
    payload = json.dumps({
        "timestamp": int(time.time()),
        "action": action,
        "details": details
    })
    result = db.record(payload, json.dumps(rules))
    data = json.loads(result) if isinstance(result, str) else result
    return data.get("latest_hash") or (data.get("output") or {}).get("latest_hash")

def main():
    for f in [DB, KEYS]:
        if os.path.exists(f): os.remove(f)

    gen_keys(KEYS)
    db = TempusDDB("tmb_live_agent", DB, KEYS)

    print("Agent starting mission...")

    # Decision 1
    h1 = agent_decide(db, "scan_environment", {"sensors": ["lidar", "camera"]}, {"risk": "low"})
    print(f"1. Environment scanned. Hash: {h1}")

    # Decision 2 - chained
    h2 = db.record(
        json.dumps({"action": "approach_target", "distance": 50}),
        json.dumps({"safety_distance": 30}),
        parent=h1
    )
    h2 = json.loads(h2).get("latest_hash") if isinstance(h2, str) else h2
    print(f"2. Approached target. Hash: {h2}")

    # Decision 3
    db.record(
        json.dumps({"action": "execute_mission", "result": "success"}),
        json.dumps({"confirmation_required": True}),
        parent=h2
    )
    print("3. Mission executed.")

    print("\nFinal verification:")
    print(db.validate())

    print("\n✅ Full auditable agent flow completed.")

if __name__ == "__main__":
    main()
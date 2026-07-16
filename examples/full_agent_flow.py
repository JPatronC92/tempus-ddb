"""End-to-end autonomous B2A authorization and execution example."""

import json
import os
import time

from tempus_ddb import TempusDDB, gen_keys


DB = "agent_flow.db"
GATE_KEYS = "agent_flow_gate.keys.json"
AGENT_KEYS = "agent_flow_agent.keys.json"
EXECUTOR_KEYS = "agent_flow_executor.keys.json"


def public_key(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)["public_key"]


def main():
    for path in [DB, GATE_KEYS, AGENT_KEYS, EXECUTOR_KEYS]:
        if os.path.exists(path):
            os.remove(path)

    for path in [GATE_KEYS, AGENT_KEYS, EXECUTOR_KEYS]:
        gen_keys(path)

    gate_id = public_key(GATE_KEYS)
    agent_id = public_key(AGENT_KEYS)
    executor_id = public_key(EXECUTOR_KEYS)
    gate = TempusDDB(DB, GATE_KEYS)
    gate.register_agent(gate_id, "tempus-gate", '{"can_delegate":true}')
    gate.register_agent(agent_id, "mission-agent", "{}")
    gate.register_agent(executor_id, "mission-executor", "{}")

    intent = json.dumps({
        "schema_version": "tempus.action-intent.v1",
        "tenant_id": "example-org",
        "agent_id": agent_id,
        "idempotency_key": "mission-001",
        "action_type": "execute_mission",
        "resource": "robot/fleet-7",
        "requested_at": time.time_ns() // 1_000,
        "input": {"target": "zone-4", "safety_distance": 30},
        "money": None,
    })
    authorization = json.loads(gate.request_action(intent, AGENT_KEYS, 60))
    permit = authorization["authorization"]
    print(f"Authorization: {permit['decision']} ({permit['authorization_id']})")
    if permit["decision"] != "ALLOWED":
        print("Mission was blocked before execution.")
        return

    # A real executor verifies the permit, then uses credentials unavailable to
    # the requesting agent. This sample effect is intentionally local.
    observed_result = {"target_reached": True, "distance_maintained": 35}
    outcome = json.dumps({
        "schema_version": "tempus.action-outcome.v1",
        "authorization_id": permit["authorization_id"],
        "action_id": permit["action_id"],
        "status": "SUCCEEDED",
        "external_reference": "robot-run-001",
        "output": observed_result,
    })
    receipt = json.loads(
        gate.commit_outcome(permit["authorization_id"], outcome, EXECUTOR_KEYS)
    )
    verification = json.loads(gate.verify_trace(permit["action_id"]))
    print(f"Execution receipt: {receipt['receipt']['receipt_id']}")
    print(json.dumps(verification, indent=2))


if __name__ == "__main__":
    main()

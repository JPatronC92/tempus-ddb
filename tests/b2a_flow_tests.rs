use _tempus_ddb::{generate_keypair, SqliteStorage};
use rusqlite::Connection;
use serde_json::{json, Value};
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

fn public_key(path: &Path) -> String {
    let value: Value = serde_json::from_str(&std::fs::read_to_string(path).unwrap()).unwrap();
    value["public_key"].as_str().unwrap().to_string()
}

fn parse(value: &str) -> Value {
    serde_json::from_str(value).unwrap()
}

fn intent(agent_id: &str, idempotency_key: &str, resource: &str) -> String {
    let requested_at = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_micros() as u64;
    json!({
        "schema_version": "tempus.action-intent.v1",
        "tenant_id": "acme",
        "agent_id": agent_id,
        "idempotency_key": idempotency_key,
        "action_type": "purchase",
        "resource": resource,
        "requested_at": requested_at,
        "input": {"sku": "compute-credits"},
        "money": {"amount": "25.00", "asset": "USD", "beneficiary": "vendor-42"}
    })
    .to_string()
}

#[test]
fn b2a_authorize_execute_verify_and_replay_guards() {
    let temp = tempfile::tempdir().unwrap();
    let db_path = temp.path().join("tempus.db");
    let gate_keyfile = temp.path().join("gate.keys.json");
    let agent_keyfile = temp.path().join("agent.keys.json");
    let executor_keyfile = temp.path().join("executor.keys.json");
    let other_keyfile = temp.path().join("other.keys.json");
    generate_keypair(gate_keyfile.to_str().unwrap()).unwrap();
    generate_keypair(agent_keyfile.to_str().unwrap()).unwrap();
    generate_keypair(executor_keyfile.to_str().unwrap()).unwrap();
    generate_keypair(other_keyfile.to_str().unwrap()).unwrap();

    let gate_id = public_key(&gate_keyfile);
    let agent_id = public_key(&agent_keyfile);
    let executor_id = public_key(&executor_keyfile);
    let other_id = public_key(&other_keyfile);
    let storage = SqliteStorage::new(
        db_path.to_str().unwrap().to_string(),
        gate_keyfile.to_str().unwrap().to_string(),
    )
    .unwrap();

    let root = parse(
        &storage
            .register_agent(&gate_id, "tempus-gate", r#"{"can_delegate":true}"#)
            .unwrap(),
    );
    assert_eq!(root["registration"]["registered_by"], gate_id);
    assert!(storage.verify_agent(&gate_id).unwrap());
    storage
        .register_agent(&agent_id, "buyer-agent", "{}")
        .unwrap();
    storage
        .register_agent(&executor_id, "purchase-executor", "{}")
        .unwrap();
    assert!(storage.verify_agent(&agent_id).unwrap());
    assert!(storage
        .register_agent(&agent_id, "renamed-agent", "{}")
        .unwrap_err()
        .contains("TEMPUS_AGENT_ALREADY_REGISTERED"));

    let request = intent(&agent_id, "purchase-001", "vendor-api/credits");
    let authorization_json = storage
        .request_action(&request, agent_keyfile.to_str().unwrap(), 60)
        .unwrap();
    let authorization = parse(&authorization_json);
    assert_eq!(
        authorization["schema_version"],
        "tempus.authorization-result.v1"
    );
    assert_eq!(authorization["authorization"]["decision"], "ALLOWED");
    let authorization_id = authorization["authorization"]["authorization_id"]
        .as_str()
        .unwrap();
    let action_id = authorization["authorization"]["action_id"]
        .as_str()
        .unwrap();

    let duplicate = storage
        .request_action(&request, agent_keyfile.to_str().unwrap(), 60)
        .unwrap();
    assert_eq!(
        parse(&duplicate)["authorization"]["authorization_id"],
        authorization_id
    );
    let conflict = intent(&agent_id, "purchase-001", "different-resource");
    assert!(storage
        .request_action(&conflict, agent_keyfile.to_str().unwrap(), 60)
        .unwrap_err()
        .contains("TEMPUS_IDEMPOTENCY_CONFLICT"));

    let outcome = json!({
        "schema_version": "tempus.action-outcome.v1",
        "authorization_id": authorization_id,
        "action_id": action_id,
        "status": "SUCCEEDED",
        "external_reference": "vendor-tx-9182",
        "output": {"credits_added": 1000}
    })
    .to_string();
    let execution_json = storage
        .commit_outcome(
            authorization_id,
            &outcome,
            executor_keyfile.to_str().unwrap(),
        )
        .unwrap();
    let execution = parse(&execution_json);
    assert_eq!(execution["receipt"]["status"], "SUCCEEDED");

    let duplicate_execution = storage
        .commit_outcome(
            authorization_id,
            &outcome,
            executor_keyfile.to_str().unwrap(),
        )
        .unwrap();
    assert_eq!(
        parse(&duplicate_execution)["receipt"]["receipt_id"],
        execution["receipt"]["receipt_id"]
    );
    let conflicting_outcome = json!({
        "schema_version": "tempus.action-outcome.v1",
        "authorization_id": authorization_id,
        "action_id": action_id,
        "status": "FAILED",
        "error": "late conflicting result"
    })
    .to_string();
    assert!(storage
        .commit_outcome(
            authorization_id,
            &conflicting_outcome,
            executor_keyfile.to_str().unwrap(),
        )
        .unwrap_err()
        .contains("TEMPUS_PERMIT_ALREADY_CONSUMED"));

    let verification = parse(&storage.verify_trace(action_id).unwrap());
    assert_eq!(verification["status"], "VERIFIED");
    assert_eq!(verification["phase"], "COMPLETED");
    let trace = parse(&storage.get_trace(action_id).unwrap());
    assert_eq!(trace["execution"]["receipt"]["executor_id"], executor_id);

    let unregistered_intent = intent(&other_id, "unregistered-001", "email/send");
    let blocked = parse(
        &storage
            .request_action(&unregistered_intent, other_keyfile.to_str().unwrap(), 60)
            .unwrap(),
    );
    assert_eq!(blocked["authorization"]["decision"], "BLOCKED");
    let blocked_action = blocked["authorization"]["action_id"].as_str().unwrap();
    let blocked_verification = parse(&storage.verify_trace(blocked_action).unwrap());
    assert_eq!(blocked_verification["status"], "VERIFIED");
    assert_eq!(blocked_verification["phase"], "BLOCKED");

    let stale_intent = json!({
        "schema_version": "tempus.action-intent.v1",
        "tenant_id": "acme",
        "agent_id": agent_id,
        "idempotency_key": "stale-001",
        "action_type": "send_email",
        "resource": "mail/outbox",
        "requested_at": 1,
        "input": {}
    })
    .to_string();
    let stale = parse(
        &storage
            .request_action(&stale_intent, agent_keyfile.to_str().unwrap(), 60)
            .unwrap(),
    );
    assert_eq!(stale["authorization"]["decision"], "BLOCKED");
    assert_eq!(stale["authorization"]["reason_codes"][0], "REQUEST_STALE");

    let invalid_signature_intent = intent(&agent_id, "invalid-signature-001", "mail/outbox");
    let invalid_signature = parse(
        &storage
            .request_action_signed(&invalid_signature_intent, &agent_id, &"00".repeat(64), 60)
            .unwrap(),
    );
    assert_eq!(invalid_signature["authorization"]["decision"], "BLOCKED");
    let invalid_signature_action = invalid_signature["authorization"]["action_id"]
        .as_str()
        .unwrap();
    assert_eq!(
        parse(&storage.verify_trace(invalid_signature_action).unwrap())["status"],
        "VERIFIED"
    );

    let agent_storage = SqliteStorage::new(
        db_path.to_str().unwrap().to_string(),
        agent_keyfile.to_str().unwrap().to_string(),
    )
    .unwrap();
    assert!(agent_storage
        .register_agent(&other_id, "unauthorized-delegation", "{}")
        .unwrap_err()
        .contains("TEMPUS_REGISTRAR_NOT_AUTHORIZED"));
}

#[test]
fn trace_verification_detects_receipt_tampering() {
    let temp = tempfile::tempdir().unwrap();
    let db_path = temp.path().join("tempus.db");
    let gate_keyfile = temp.path().join("gate.keys.json");
    let agent_keyfile = temp.path().join("agent.keys.json");
    generate_keypair(gate_keyfile.to_str().unwrap()).unwrap();
    generate_keypair(agent_keyfile.to_str().unwrap()).unwrap();
    let gate_id = public_key(&gate_keyfile);
    let agent_id = public_key(&agent_keyfile);
    let storage = SqliteStorage::new(
        db_path.to_str().unwrap().to_string(),
        gate_keyfile.to_str().unwrap().to_string(),
    )
    .unwrap();
    storage.register_agent(&gate_id, "gate", "{}").unwrap();
    storage.register_agent(&agent_id, "agent", "{}").unwrap();
    let authorization = parse(
        &storage
            .request_action(
                &intent(&agent_id, "tamper-001", "calendar/create"),
                agent_keyfile.to_str().unwrap(),
                60,
            )
            .unwrap(),
    );
    let action_id = authorization["authorization"]["action_id"]
        .as_str()
        .unwrap();

    let connection = Connection::open(&db_path).unwrap();
    connection
        .execute(
            "UPDATE action_authorizations
             SET authorization_json = replace(authorization_json, 'POLICY_ALLOWED', 'POLICY_BYPASSED')
             WHERE action_id = ?1",
            [action_id],
        )
        .unwrap();
    let verification = parse(&storage.verify_trace(action_id).unwrap());
    assert_eq!(verification["status"], "INVALID");
    assert!(verification["errors"]
        .as_array()
        .unwrap()
        .iter()
        .any(|error| error == "AUTHORIZATION_ID_MISMATCH"));
}

use serde_json::Value;
use std::process::Command;
use tempfile::tempdir;

// Run the tempus-ddb binary
fn run_cli(args: &[&str]) -> (bool, String, String) {
    let output = Command::new(env!("CARGO_BIN_EXE_tempus-ddb"))
        .args(args)
        .output()
        .expect("Failed to execute process");

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    (output.status.success(), stdout, stderr)
}

#[test]
fn test_end_to_end_flow() {
    let dir = tempdir().unwrap();
    let db_path_buf = dir.path().join("db.sqlite");
    let key_path_buf = dir.path().join("keys.json");
    let db_path = db_path_buf.to_str().unwrap();
    let key_path = key_path_buf.to_str().unwrap();

    // Init DB
    let (success, _, _) = run_cli(&["init", "--db", db_path]);
    assert!(success, "Init failed");

    // Generate keys
    let (success, _, _) = run_cli(&["gen-keys", "--output", key_path]);
    assert!(success, "Gen keys failed");

    // Record Genesis Decision
    let payload = r#"{"action": "create_user"}"#;
    let rules = r#"{"rule": "allow"}"#;
    let (success, stdout, _) = run_cli(&[
        "record",
        "--db",
        db_path,
        "--keyfile",
        key_path,
        "--payload",
        payload,
        "--rules",
        rules,
        "--genesis",
    ]);
    assert!(success, "Record genesis failed");

    let genesis_decision: Value = serde_json::from_str(&stdout).expect("Failed to parse output");
    let genesis_hash = genesis_decision["latest_hash"].as_str().unwrap();

    // Attempting a second genesis should fail
    let (success, _, stderr) = run_cli(&[
        "record",
        "--db",
        db_path,
        "--keyfile",
        key_path,
        "--payload",
        payload,
        "--rules",
        rules,
        "--genesis",
    ]);
    assert!(!success, "Second genesis should fail");
    assert!(
        stderr.contains("A genesis decision already exists"),
        "Unexpected error message"
    );

    // Record Child Decision
    let child_payload = r#"{"action": "update_user"}"#;
    let (success, stdout, _) = run_cli(&[
        "record",
        "--db",
        db_path,
        "--keyfile",
        key_path,
        "--payload",
        child_payload,
        "--rules",
        rules,
    ]);
    assert!(success, "Record child failed");

    let child_decision: Value = serde_json::from_str(&stdout).unwrap();
    assert_eq!(child_decision["status"], "success");
    assert!(child_decision["latest_hash"].as_str().is_some());

    // Validate Ledger
    let (success, stdout, _) = run_cli(&["validate", "--db", db_path]);
    assert!(success, "Validate failed");
    assert!(stdout.contains("valid"), "Validation should report valid");

    // Export Ledger
    let (success, stdout, _) = run_cli(&["export", "--db", db_path]);
    assert!(success, "Export failed");
    let export_res: Value = serde_json::from_str(&stdout).unwrap();
    let export_arr = export_res.as_array().unwrap();
    assert_eq!(export_arr.len(), 2);
    assert_eq!(export_arr[0]["id"].as_str().unwrap(), genesis_hash);
}

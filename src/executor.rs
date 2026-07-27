use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use rusqlite::{params, Connection};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::fs;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

pub trait ExecutorStorage {
    fn initialize(&self) -> Result<(), String>;
    fn start_consumption(&self, authorization_id: &str, action_id: &str) -> Result<(), String>;
    fn complete_consumption(&self, authorization_id: &str, outcome: &str) -> Result<(), String>;
}

pub struct SqliteExecutorStorage {
    db_path: String,
}

impl SqliteExecutorStorage {
    pub fn new(db_path: &str) -> Self {
        Self {
            db_path: db_path.to_string(),
        }
    }

    fn get_connection(&self) -> Result<Connection, String> {
        Connection::open(&self.db_path).map_err(|e| e.to_string())
    }
}

impl ExecutorStorage for SqliteExecutorStorage {
    fn initialize(&self) -> Result<(), String> {
        let conn = self.get_connection()?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS consumed_permits (
                authorization_id TEXT PRIMARY KEY,
                action_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL, -- 'STARTED', 'COMPLETED', 'FAILED'
                started_at INTEGER NOT NULL,
                completed_at INTEGER,
                outcome TEXT
            );",
        )
        .map_err(|e| e.to_string())
    }

    fn start_consumption(&self, authorization_id: &str, action_id: &str) -> Result<(), String> {
        let mut conn = self.get_connection()?;
        let tx = conn.transaction().map_err(|e| e.to_string())?;

        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_millis() as u64;

        tx.execute(
            "INSERT INTO consumed_permits (authorization_id, action_id, status, started_at)
             VALUES (?1, ?2, 'STARTED', ?3)",
            params![authorization_id, action_id, now],
        )
        .map_err(|e| {
            if e.to_string().contains("UNIQUE constraint failed") {
                "Permit already consumed or action ID re-used".to_string()
            } else {
                e.to_string()
            }
        })?;

        tx.commit().map_err(|e| e.to_string())
    }

    fn complete_consumption(&self, authorization_id: &str, outcome: &str) -> Result<(), String> {
        let mut conn = self.get_connection()?;
        let tx = conn.transaction().map_err(|e| e.to_string())?;

        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_millis() as u64;

        let rows = tx
            .execute(
                "UPDATE consumed_permits SET status = 'COMPLETED', completed_at = ?1, outcome = ?2
             WHERE authorization_id = ?3 AND status = 'STARTED'",
                params![now, outcome, authorization_id],
            )
            .map_err(|e| e.to_string())?;

        if rows == 0 {
            return Err("Consumption not found or already completed".to_string());
        }

        tx.commit().map_err(|e| e.to_string())
    }
}

pub struct MediatedExecutor {
    storage: Box<dyn ExecutorStorage + Send>,
    keypair: SigningKey,
}

impl MediatedExecutor {
    pub fn new(storage: Box<dyn ExecutorStorage + Send>, keyfile: &str) -> Result<Self, String> {
        let keypair = Self::load_keypair(keyfile)?;
        storage.initialize()?;
        Ok(Self { storage, keypair })
    }

    fn load_keypair(path: &str) -> Result<SigningKey, String> {
        let content = fs::read_to_string(Path::new(path)).map_err(|e| e.to_string())?;
        let parsed: Value = serde_json::from_str(&content).map_err(|e| e.to_string())?;
        let sk_hex = parsed
            .get("private_key")
            .and_then(|v| v.as_str())
            .ok_or("Missing private_key in keyfile")?;
        let mut sk_bytes = [0u8; 32];
        hex::decode_to_slice(sk_hex, &mut sk_bytes).map_err(|e| e.to_string())?;
        Ok(SigningKey::from_bytes(&sk_bytes))
    }

    pub fn verify_and_consume_permit(&self, permit_json: &str) -> Result<Value, String> {
        let permit: Value = serde_json::from_str(permit_json).map_err(|e| e.to_string())?;

        let schema = permit.get("schema_version").and_then(|v| v.as_str());
        if schema != Some("tempus.authorization-result.v1") {
            return Err("Invalid permit schema".to_string());
        }

        let authorization = permit.get("authorization").ok_or("Missing authorization")?;
        let gate_signature_hex = authorization
            .get("gate_signature")
            .and_then(|v| v.as_str())
            .ok_or("Missing gate_signature")?;

        let gate_id_hex = authorization
            .get("gate_id")
            .and_then(|v| v.as_str())
            .ok_or("Missing gate_id")?;
        let mut pk_bytes = [0u8; 32];
        hex::decode_to_slice(gate_id_hex, &mut pk_bytes).map_err(|e| e.to_string())?;
        let gate_vk = VerifyingKey::from_bytes(&pk_bytes).map_err(|_| "Invalid gate pk")?;

        let mut sig_bytes = [0u8; 64];
        hex::decode_to_slice(gate_signature_hex, &mut sig_bytes).map_err(|e| e.to_string())?;
        let signature = Signature::from_bytes(&sig_bytes);

        let authorization_id = authorization
            .get("authorization_id")
            .and_then(|v| v.as_str())
            .ok_or("Missing authorization_id")?;

        let mut auth_clone = authorization.clone();
        auth_clone
            .as_object_mut()
            .unwrap()
            .remove("authorization_id");
        auth_clone.as_object_mut().unwrap().remove("gate_signature");
        let canonical_auth = crate::b2a::canonicalize(&auth_clone)?;

        let mut hasher = Sha256::new();
        hasher.update(canonical_auth.as_bytes());
        let digest_bytes = hasher.finalize();

        if hex::encode(digest_bytes) != authorization_id {
            return Err("Authorization ID mismatch".to_string());
        }

        let digest = hex::decode(authorization_id).map_err(|e| e.to_string())?;
        gate_vk
            .verify(&digest, &signature)
            .map_err(|_| "Invalid gate signature")?;

        if authorization.get("decision").and_then(|v| v.as_str()) != Some("ALLOWED") {
            return Err("Permit is not ALLOWED".to_string());
        }

        let expires_at = authorization
            .get("expires_at")
            .and_then(|v| v.as_u64())
            .ok_or("Missing expires_at")?;
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_micros() as u64;

        if now > expires_at {
            return Err("Permit has expired".to_string());
        }

        let action_id = authorization
            .get("action_id")
            .and_then(|v| v.as_str())
            .ok_or("Missing action_id")?;

        self.storage
            .start_consumption(authorization_id, action_id)?;

        Ok(authorization.clone())
    }

    pub fn complete_execution(
        &self,
        authorization_id: &str,
        action_id: &str,
        status: &str,
        output: Value,
    ) -> Result<String, String> {
        let mut outcome = json!({
            "schema_version": "tempus.action-outcome.v1",
            "authorization_id": authorization_id,
            "action_id": action_id,
            "status": status,
            "executor_id": hex::encode(self.keypair.verifying_key().as_bytes()),
            "output": output
        });

        let outcome_str = serde_json::to_string(&outcome).unwrap();
        let mut hasher = Sha256::new();
        hasher.update(outcome_str.as_bytes());
        let digest = hasher.finalize();

        let signature = self.keypair.sign(&digest);
        outcome["executor_signature"] = json!(hex::encode(signature.to_bytes()));

        let final_outcome_str = serde_json::to_string(&outcome).unwrap();
        self.storage
            .complete_consumption(authorization_id, &final_outcome_str)?;

        Ok(final_outcome_str)
    }
}

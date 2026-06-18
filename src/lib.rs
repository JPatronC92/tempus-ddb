#[cfg(not(target_arch = "wasm32"))]
use pyo3::prelude::*;
#[cfg(not(target_arch = "wasm32"))]
use pyo3::exceptions::PyPermissionError;

#[cfg(target_arch = "wasm32")]
use wasm_bindgen::prelude::*;

// --- 1. LÓGICA DE SEGURIDAD COMÚN (GATEKEEPER) ---

/// HMAC secret used for license key verification.
/// NOTE: In production, this would be fetched from a secure server or HSM,
/// not hardcoded. This is a placeholder for the HMAC-based verification scheme.
const LICENSE_SECRET: &[u8] = b"tempus-ddb-hmac-secret-key-v1-2026";

/// Verify a license key using HMAC-SHA256.
///
/// Expected format: `tmb_live_{random_part}_{hmac_hex_signature}`
///
/// The HMAC is computed over the random_part using LICENSE_SECRET.
/// Both the prefix and the cryptographic signature must be valid.
fn check_license(license_key: &str) -> Result<(), String> {
    use hmac::{Hmac, Mac};
    use sha2::Sha256;

    type HmacSha256 = Hmac<Sha256>;

    let prefix = "tmb_live_";

    if !license_key.starts_with(prefix) {
        return Err("TempusDDB Auth Error: Invalid license key format (missing prefix).".to_string());
    }

    let without_prefix = &license_key[prefix.len()..];

    // The format after the prefix is: {random_part}_{hmac_signature}
    // Find the LAST underscore to split random_part from the HMAC signature,
    // since the random_part itself should not contain underscores but we
    // use rfind for robustness.
    let last_underscore = without_prefix.rfind('_').ok_or_else(|| {
        "TempusDDB Auth Error: Invalid license key format (missing HMAC signature).".to_string()
    })?;

    let random_part = &without_prefix[..last_underscore];
    let provided_hmac_hex = &without_prefix[last_underscore + 1..];

    if random_part.is_empty() || provided_hmac_hex.is_empty() {
        return Err("TempusDDB Auth Error: Invalid license key format (empty components).".to_string());
    }

    // Decode the provided HMAC hex
    let provided_hmac_bytes = hex::decode(provided_hmac_hex).map_err(|_| {
        "TempusDDB Auth Error: Invalid license key (malformed HMAC signature).".to_string()
    })?;

    // Compute HMAC-SHA256 of the random part
    let mut mac = HmacSha256::new_from_slice(LICENSE_SECRET)
        .map_err(|_| "TempusDDB Auth Error: Internal HMAC initialization failure.".to_string())?;
    mac.update(random_part.as_bytes());

    // Verify (constant-time comparison)
    mac.verify_slice(&provided_hmac_bytes).map_err(|_| {
        "TempusDDB Auth Error: License key is invalid, revoked, or expired.".to_string()
    })?;

    Ok(())
}

// --- 2. PATRÓN STORAGE LAYER (TRAIT) ---
pub trait StorageLayer {
    fn insert_decision(&mut self, payload: &str, rules: &str, genesis: bool) -> Result<(), String>;
    fn get_latest_hash(&self) -> Result<String, String>;
    fn export_ledger(&self) -> Result<String, String>;
}

// Implementación en Memoria (Para el Ecosistema WASM / JS)
#[cfg(target_arch = "wasm32")]
pub struct MemoryStorage {
    records: Vec<String>,
    latest_hash: String,
}

#[cfg(target_arch = "wasm32")]
impl MemoryStorage {
    pub fn new() -> Self {
        Self { 
            records: Vec::new(),
            latest_hash: "GENESIS_HASH_MEM".to_string(),
        }
    }
}

#[cfg(target_arch = "wasm32")]
impl StorageLayer for MemoryStorage {
    fn insert_decision(&mut self, payload: &str, _rules: &str, genesis: bool) -> Result<(), String> {
        self.records.push(payload.to_string());
        if genesis {
            self.latest_hash = "GENESIS_HASH_MEM".to_string();
        } else {
            self.latest_hash = "NEW_HASH_MEM".to_string(); // Simulación de nuevo hash
        }
        Ok(())
    }

    fn get_latest_hash(&self) -> Result<String, String> {
        Ok(self.latest_hash.clone())
    }

    fn export_ledger(&self) -> Result<String, String> {
        // En una implementación real, serializaríamos a JSON usando serde_json
        Ok(format!("[{}]", self.records.join(",")))
    }
}

// Implementación SQLite (Para Python / Nativo)
#[cfg(not(target_arch = "wasm32"))]
use rusqlite::Connection;

#[cfg(not(target_arch = "wasm32"))]
use serde::{Serialize, Deserialize};

#[cfg(not(target_arch = "wasm32"))]
use sha2::{Digest, Sha256};

#[cfg(not(target_arch = "wasm32"))]
use ed25519_dalek::Signer;

#[cfg(not(target_arch = "wasm32"))]
#[derive(Debug, Serialize, Deserialize, Clone)]
struct Decision {
    id: String,
    parent_id: String,
    causal_depth: u64,
    actor_id: String,
    timestamp: u64,
    payload: String,
    rules_evaluated: String,
    signature: String,
}

#[cfg(not(target_arch = "wasm32"))]
pub struct SqliteStorage {
    conn: Connection,
    keyfile: String,
}

#[cfg(not(target_arch = "wasm32"))]
impl SqliteStorage {
    pub fn new(db_path: String, keyfile: String) -> Result<Self, String> {
        let conn = Connection::open(&db_path)
            .map_err(|e| format!("Failed to open SQLite database '{}': {}", db_path, e))?;

        conn.execute(
            "CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                parent_id TEXT NOT NULL,
                causal_depth INTEGER NOT NULL,
                actor_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                payload TEXT NOT NULL,
                rules_evaluated TEXT NOT NULL,
                signature TEXT NOT NULL
            );",
            [],
        ).map_err(|e| format!("Failed to create decisions table: {}", e))?;

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_parent_id ON decisions (parent_id);",
            [],
        ).map_err(|e| format!("Failed to create parent index: {}", e))?;

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_causal_depth ON decisions (causal_depth);",
            [],
        ).map_err(|e| format!("Failed to create causal depth index: {}", e))?;

        Ok(Self { conn, keyfile })
    }

    /// Load an Ed25519 signing key from the keyfile on disk.
    fn load_signing_key(&self) -> Result<ed25519_dalek::SigningKey, String> {
        #[derive(Deserialize)]
        struct KeyPairConfig {
            #[allow(dead_code)]
            public_key: String,
            private_key: String,
        }

        let content = std::fs::read_to_string(&self.keyfile)
            .map_err(|e| format!("Failed to read key file '{}': {}", self.keyfile, e))?;
        let config: KeyPairConfig = serde_json::from_str(&content)
            .map_err(|e| format!("Failed to parse key file JSON: {}", e))?;

        let private_key_bytes = hex::decode(&config.private_key)
            .map_err(|e| format!("Invalid private key hex: {}", e))?;
        let private_key_array: [u8; 32] = private_key_bytes.try_into()
            .map_err(|_| "Private key must be exactly 32 bytes".to_string())?;

        Ok(ed25519_dalek::SigningKey::from_bytes(&private_key_array))
    }

    /// Compute the canonical SHA-256 hash for a decision (matches main.rs logic).
    fn calculate_canonical_hash(
        parent_id: &str,
        actor_id: &str,
        timestamp: u64,
        payload: &str,
        rules_evaluated: &str,
    ) -> String {
        let canonical = format!(
            "parent_id:{}\nactor_id:{}\ntimestamp:{}\npayload:{}\nrules:{}\n",
            parent_id, actor_id, timestamp, payload, rules_evaluated
        );

        let mut hasher = Sha256::new();
        hasher.update(canonical.as_bytes());
        let result = hasher.finalize();
        hex::encode(result)
    }

    /// Get the last recorded decision (by causal depth descending).
    fn get_last_decision(&self) -> Result<Option<Decision>, String> {
        let mut stmt = self.conn.prepare(
            "SELECT id, parent_id, causal_depth, actor_id, timestamp, payload, rules_evaluated, signature
             FROM decisions
             ORDER BY causal_depth DESC, timestamp DESC
             LIMIT 1"
        ).map_err(|e| format!("Failed to prepare select statement: {}", e))?;

        let mut rows = stmt.query([]).map_err(|e| format!("Failed to query database: {}", e))?;
        if let Some(row) = rows.next().map_err(|e| format!("Error advancing row: {}", e))? {
            Ok(Some(Decision {
                id: row.get(0).unwrap(),
                parent_id: row.get(1).unwrap(),
                causal_depth: row.get(2).unwrap(),
                actor_id: row.get(3).unwrap(),
                timestamp: row.get(4).unwrap(),
                payload: row.get(5).unwrap(),
                rules_evaluated: row.get(6).unwrap(),
                signature: row.get(7).unwrap(),
            }))
        } else {
            Ok(None)
        }
    }
}

#[cfg(not(target_arch = "wasm32"))]
impl StorageLayer for SqliteStorage {
    fn insert_decision(&mut self, payload: &str, rules: &str, genesis: bool) -> Result<(), String> {
        // Validate payload and rules are valid JSON
        serde_json::from_str::<serde_json::Value>(payload)
            .map_err(|e| format!("Payload is not valid JSON: {}", e))?;
        serde_json::from_str::<serde_json::Value>(rules)
            .map_err(|e| format!("Rules is not valid JSON: {}", e))?;

        // Load signing key from keyfile
        let signing_key = self.load_signing_key()?;
        let verifying_key = signing_key.verifying_key();
        let actor_id = hex::encode(verifying_key.to_bytes());

        // Resolve parent_id and causal_depth
        let (parent_id, causal_depth) = match self.get_last_decision()? {
            Some(last_d) => {
                if genesis {
                    // Even if there are existing decisions, --genesis forces a new root
                    ("genesis".to_string(), 0u64)
                } else {
                    (last_d.id, last_d.causal_depth + 1)
                }
            }
            None => {
                if genesis {
                    ("genesis".to_string(), 0u64)
                } else {
                    return Err("Database is empty. Use genesis=true to record the first decision.".to_string());
                }
            }
        };

        // Timestamp in microseconds
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::SystemTime::UNIX_EPOCH)
            .map_err(|e| format!("System time error: {}", e))?
            .as_micros() as u64;

        // Compute the deterministic SHA-256 hash
        let id = Self::calculate_canonical_hash(&parent_id, &actor_id, timestamp, payload, rules);

        // Ed25519 signature of the hash
        let signature_struct = signing_key.sign(id.as_bytes());
        let signature = hex::encode(signature_struct.to_bytes());

        // Insert into SQLite
        self.conn.execute(
            "INSERT INTO decisions (id, parent_id, causal_depth, actor_id, timestamp, payload, rules_evaluated, signature)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            (
                &id,
                &parent_id,
                causal_depth,
                &actor_id,
                timestamp,
                payload,
                rules,
                &signature,
            ),
        ).map_err(|e| format!("Failed to insert decision into SQLite: {}", e))?;

        Ok(())
    }

    fn get_latest_hash(&self) -> Result<String, String> {
        let mut stmt = self.conn.prepare(
            "SELECT id FROM decisions ORDER BY causal_depth DESC, timestamp DESC LIMIT 1"
        ).map_err(|e| format!("Failed to prepare select statement: {}", e))?;

        let mut rows = stmt.query([]).map_err(|e| format!("Failed to query database: {}", e))?;
        if let Some(row) = rows.next().map_err(|e| format!("Error advancing row: {}", e))? {
            let id: String = row.get(0).unwrap();
            Ok(id)
        } else {
            Ok("GENESIS".to_string())
        }
    }

    fn export_ledger(&self) -> Result<String, String> {
        let mut stmt = self.conn.prepare(
            "SELECT id, parent_id, causal_depth, actor_id, timestamp, payload, rules_evaluated, signature
             FROM decisions
             ORDER BY causal_depth ASC, timestamp ASC"
        ).map_err(|e| format!("Failed to prepare select statement: {}", e))?;

        let rows = stmt.query_map([], |row| {
            Ok(Decision {
                id: row.get(0)?,
                parent_id: row.get(1)?,
                causal_depth: row.get(2)?,
                actor_id: row.get(3)?,
                timestamp: row.get(4)?,
                payload: row.get(5)?,
                rules_evaluated: row.get(6)?,
                signature: row.get(7)?,
            })
        }).map_err(|e| format!("Failed to execute query: {}", e))?;

        let mut decisions = Vec::new();
        for r in rows {
            match r {
                Ok(d) => decisions.push(d),
                Err(e) => return Err(format!("Error reading record: {}", e)),
            }
        }

        serde_json::to_string(&decisions)
            .map_err(|e| format!("Failed to serialize ledger to JSON: {}", e))
    }
}

// --- 3. BINDINGS PARA PYTHON (PYO3) ---
#[cfg(not(target_arch = "wasm32"))]
#[pyclass]
pub struct TempusDDB {
    license_key: String,
    storage: SqliteStorage,
    #[allow(dead_code)]
    keyfile: String,
}

#[cfg(not(target_arch = "wasm32"))]
#[pymethods]
impl TempusDDB {
    #[new]
    fn new(license_key: String, db_path: String, keyfile: String) -> PyResult<Self> {
        let storage = SqliteStorage::new(db_path, keyfile.clone())
            .map_err(|e| PyPermissionError::new_err(e))?;
        Ok(TempusDDB { license_key, storage, keyfile })
    }

    #[allow(unused_variables)]
    #[pyo3(signature = (payload, rules, genesis=false))]
    fn record(&mut self, payload: &str, rules: &str, genesis: bool) -> PyResult<String> {
        if let Err(e) = check_license(&self.license_key) {
            return Err(PyPermissionError::new_err(e));
        }

        self.storage.insert_decision(payload, rules, genesis).map_err(|e| PyPermissionError::new_err(e))?;

        let result_json = format!(
            r#"{{"status": "success", "action": "recorded", "latest_hash": "{}"}}"#,
            self.storage.get_latest_hash().unwrap_or_default()
        );
        Ok(result_json)
    }
}

#[cfg(not(target_arch = "wasm32"))]
#[pymodule]
fn tempus_ddb(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<TempusDDB>()?;
    Ok(())
}

// --- 4. BINDINGS PARA JAVASCRIPT (WASM-BINDGEN) ---
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen]
pub struct TempusDDBWasm {
    license_key: String,
    storage: MemoryStorage,
    keyfile: String,
}

#[cfg(target_arch = "wasm32")]
#[wasm_bindgen]
impl TempusDDBWasm {
    #[wasm_bindgen(constructor)]
    pub fn new(license_key: String, keyfile: String) -> Result<TempusDDBWasm, JsValue> {
        let storage = MemoryStorage::new();
        Ok(TempusDDBWasm { license_key, storage, keyfile })
    }

    #[wasm_bindgen]
    pub fn record(&mut self, payload: &str, rules: &str, genesis: bool) -> Result<String, JsValue> {
        // REQUISITO CUMPLIDO: Gatekeeper intacto. Arrojará un error nativo en JS interceptable.
        if let Err(e) = check_license(&self.license_key) {
            return Err(JsValue::from_str(&e));
        }

        self.storage.insert_decision(payload, rules, genesis).map_err(|e| JsValue::from_str(&e))?;

        let result_json = format!(
            r#"{{"status": "success", "action": "recorded", "latest_hash": "{}"}}"#,
            self.storage.get_latest_hash().unwrap_or_default()
        );
        Ok(result_json)
    }
    
    #[wasm_bindgen]
    pub fn get_ledger(&self) -> Result<String, JsValue> {
        self.storage.export_ledger().map_err(|e| JsValue::from_str(&e))
    }
}

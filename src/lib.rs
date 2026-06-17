#[cfg(not(target_arch = "wasm32"))]
use pyo3::prelude::*;
#[cfg(not(target_arch = "wasm32"))]
use pyo3::exceptions::PyPermissionError;

#[cfg(target_arch = "wasm32")]
use wasm_bindgen::prelude::*;

// --- 1. LÓGICA DE SEGURIDAD COMÚN (GATEKEEPER) ---
fn check_license(license_key: &str) -> Result<(), String> {
    if !license_key.starts_with("tmb_live_") || license_key.len() < 24 {
        return Err("TempusDDB Auth Error: Licencia B2B invalida, revocada o expirada.".to_string());
    }
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
pub struct SqliteStorage {
    db_path: String,
}

#[cfg(not(target_arch = "wasm32"))]
impl SqliteStorage {
    pub fn new(db_path: String) -> Self {
        Self { db_path }
    }
}

#[cfg(not(target_arch = "wasm32"))]
impl StorageLayer for SqliteStorage {
    fn insert_decision(&mut self, _payload: &str, _rules: &str, _genesis: bool) -> Result<(), String> {
        // ... [Lógica de rusqlite] ...
        Ok(())
    }

    fn get_latest_hash(&self) -> Result<String, String> {
        Ok("LATEST_HASH_SQLITE".to_string())
    }

    fn export_ledger(&self) -> Result<String, String> {
        Ok("[]".to_string())
    }
}

// --- 3. BINDINGS PARA PYTHON (PYO3) ---
#[cfg(not(target_arch = "wasm32"))]
#[pyclass]
pub struct TempusDDB {
    license_key: String,
    storage: SqliteStorage,
    keyfile: String,
}

#[cfg(not(target_arch = "wasm32"))]
#[pymethods]
impl TempusDDB {
    #[new]
    fn new(license_key: String, db_path: String, keyfile: String) -> PyResult<Self> {
        let storage = SqliteStorage::new(db_path);
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

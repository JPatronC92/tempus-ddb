from tempus_ddb import TempusDDB

print("🚀 SDK Tempus DDB: Prueba B2B PyO3 Nativa\n")

import secrets
import string
import hmac
import hashlib

def _generate_local_license() -> str:
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(24))
    hmac_sig = hmac.new(b"tempus-ddb-hmac-secret-key-v1-2026", random_part.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"tmb_live_{random_part}_{hmac_sig}"

try:
    # 1. Instanciamos la clase de Rust directamente en Python
    print("--- TEST 1: Licencia Válida ---")
    
    import tempus_ddb
    import os
    if not os.path.exists("keys.json"):
        tempus_ddb.gen_keys("keys.json")
        
    db = TempusDDB(
        license_key=_generate_local_license(), 
        db_path="flight_recorder.db", 
        keyfile="keys.json"
    )
    
    # Invocamos el motor de Rust
    receipt = db.record(payload='{"accion": "compra"}', rules='{"limite": 10}', genesis=True)
    print(f"✅ Motor Rust ejecutado con éxito: {receipt}\n")

    # 2. Comprobando el Gatekeeper con una instancia sin licencia
    print("--- TEST 2: Licencia Expirada ---")
    db_unauthorized = TempusDDB("tmb_expired_999", "flight_recorder.db", "keys.json")
    
    # Esto provocará que Rust detenga la ejecución y lance un Error a la Pila de Python
    db_unauthorized.record(payload='{}', rules='{}', genesis=False)

except Exception as e:
    # Capturamos de forma nativa el Exception de PyO3
    print(f"❌ Gatekeeper Activado. Intercepción Nativa en Python:")
    print(f"Tipo de Error: {type(e).__name__}")
    print(f"Mensaje: {e}")

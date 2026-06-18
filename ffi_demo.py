import ctypes
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ext = ".so"
lib_path = os.path.join(BASE_DIR, "target", "debug", f"libtempus_ddb{ext}")

if not os.path.exists(lib_path):
    raise FileNotFoundError(f"¡Librería dinámica no encontrada en {lib_path}!")

tempus_lib = ctypes.CDLL(lib_path)

# Actualizar la firma para incluir license_key
tempus_lib.record_decision_ffi.argtypes = [
    ctypes.c_char_p, # license_key
    ctypes.c_char_p, # db_path
    ctypes.c_char_p, # payload
    ctypes.c_char_p, # rules
    ctypes.c_char_p, # keyfile
    ctypes.c_bool    # genesis
]
tempus_lib.record_decision_ffi.restype = ctypes.c_void_p

tempus_lib.free_string_ffi.argtypes = [ctypes.c_void_p]
tempus_lib.free_string_ffi.restype = None

def record_decision(license_key: str, db_path: str, payload: dict, rules: dict, keyfile: str, genesis: bool = False) -> dict:
    c_license = license_key.encode('utf-8')
    c_db_path = db_path.encode('utf-8')
    c_payload = json.dumps(payload).encode('utf-8')
    c_rules = json.dumps(rules).encode('utf-8')
    c_keyfile = keyfile.encode('utf-8')
    
    result_ptr = tempus_lib.record_decision_ffi(
        c_license, c_db_path, c_payload, c_rules, c_keyfile, genesis
    )
    
    try:
        c_string = ctypes.cast(result_ptr, ctypes.c_char_p).value
        return json.loads(c_string.decode('utf-8'))
    finally:
        tempus_lib.free_string_ffi(result_ptr)

print("🚀 Probando el Gatekeeper SaaS (Validación en Memoria)...")

payload = {"accion": "transferencia", "monto": 500}
rules = {"limite": 1000}

print("\n--- TEST 1: Licencia Inválida ---")
resp_fail = record_decision("tmb_expired_123", "db.db", payload, rules, "keys.json", True)
print(f"❌ Respuesta Rust: {json.dumps(resp_fail, indent=2)}")

print("\n--- TEST 2: Licencia Válida ---")
resp_ok = record_decision("tmb_live_1234567890abcdefgh", "db.db", payload, rules, "keys.json", True)
print(f"✅ Respuesta Rust: {json.dumps(resp_ok, indent=2)}")

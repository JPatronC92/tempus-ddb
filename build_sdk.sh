#!/usr/bin/env bash
set -e

echo "📦 Construyendo SDK B2B de Tempus DDB (Python Distribution)..."

# 1. Compilar el core nativo en Rust con optimizaciones de producción
cargo build --release

# 2. Crear estructura del paquete Python B2B
PACKAGE_DIR="tempus_sdk"
rm -rf $PACKAGE_DIR
mkdir -p $PACKAGE_DIR

# 3. Copiar la librería compartida compilada
# Nota: Asume extensión .so por ser Termux/Linux. En scripts universales se copia .dylib o .dll según OS.
cp target/release/libtempus_ddb.so $PACKAGE_DIR/

# 4. Generar el wrapper __init__.py automatizado y orientado a objetos
cat << 'EOF' > $PACKAGE_DIR/__init__.py
import ctypes
import json
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
_lib_path = os.path.join(_DIR, "libtempus_ddb.so")

if not os.path.exists(_lib_path):
    raise RuntimeError("Tempus DDB Core (Rust) no encontrado. SDK corrupto o arquitectura incorrecta.")

_lib = ctypes.CDLL(_lib_path)

# Mapeo estricto del contrato FFI
_lib.record_decision_ffi.argtypes = [
    ctypes.c_char_p, # license_key
    ctypes.c_char_p, # db_path
    ctypes.c_char_p, # payload
    ctypes.c_char_p, # rules
    ctypes.c_char_p, # keyfile
    ctypes.c_bool    # genesis
]
_lib.record_decision_ffi.restype = ctypes.c_void_p
_lib.free_string_ffi.argtypes = [ctypes.c_void_p]
_lib.free_string_ffi.restype = None

class TempusDDB:
    """
    Tempus DDB B2B SDK Client
    Fricción cero para clientes Python utilizando FFI ultrarrápido bajo el capó.
    """
    def __init__(self, license_key: str, db_path: str, keyfile: str):
        self.license_key = license_key.encode('utf-8')
        self.db_path = db_path.encode('utf-8')
        self.keyfile = keyfile.encode('utf-8')

    def record(self, payload: dict, rules: dict, genesis: bool = False) -> dict:
        """Sella criptográficamente una decisión inmutable en el Flight Recorder."""
        c_payload = json.dumps(payload).encode('utf-8')
        c_rules = json.dumps(rules).encode('utf-8')
        
        ptr = _lib.record_decision_ffi(
            self.license_key, self.db_path, c_payload, c_rules, self.keyfile, genesis
        )
        try:
            res_str = ctypes.cast(ptr, ctypes.c_char_p).value.decode('utf-8')
            response = json.loads(res_str)
            
            # Lanzar excepción nativa en Python si el Gatekeeper Rust detectó un problema de licencia
            if response.get("status") == "error":
                raise PermissionError(response.get("message"))
                
            return response
        finally:
            _lib.free_string_ffi(ptr)
EOF

echo "✅ SDK construido exitosamente en la carpeta '$PACKAGE_DIR/'."
echo "💡 Para usarlo en otro proyecto local: cp -r tempus_sdk /ruta/a/tu/proyecto"

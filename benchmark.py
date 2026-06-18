import time
import os
import json
from tempus_ddb import TempusDDB

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "benchmark.db")
keys_path = os.path.join(BASE_DIR, "keys.json")

# Limpiamos archivos anteriores
for f in [db_path, keys_path]:
    if os.path.exists(f):
        os.remove(f)

import secrets
import string
import hmac
import hashlib

def _generate_local_license() -> str:
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(24))
    hmac_sig = hmac.new(b"tempus-ddb-hmac-secret-key-v1-2026", random_part.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"tmb_live_{random_part}_{hmac_sig}"

# Inicializamos (asegúrate de que tu Rust genere las keys si no existen, o genéralas antes)
import tempus_ddb
if not os.path.exists(keys_path):
    tempus_ddb.gen_keys(keys_path)

db = TempusDDB(_generate_local_license(), db_path, keys_path)

print("🔥 Iniciando benchmark de 1,000 decisiones inmutables...")
start_time = time.time()

for i in range(1000):
    payload = json.dumps({"accion": "lectura", "sensor": i})
    rules = json.dumps({"limite": 100})
    # Solo el primero es génesis
    db.record(payload, rules, genesis=(i == 0))

end_time = time.time()
duracion = end_time - start_time

print(f"✅ 1,000 registros procesados y sellados criptográficamente.")
print(f"⏱️ Tiempo total: {duracion:.2f} segundos.")
print(f"🚀 Velocidad: {1000 / duracion:.2f} decisiones por segundo.")

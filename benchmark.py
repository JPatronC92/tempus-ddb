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

# Inicializamos (asegúrate de que tu Rust genere las keys si no existen, o genéralas antes)
import tempus_ddb
if not os.path.exists(keys_path):
    tempus_ddb.gen_keys(keys_path)

db = TempusDDB(db_path, keys_path)

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

import time
import os
import json
from tempus_ddb import TempusDDB

# Limpiamos archivos anteriores
for f in ["benchmark.db", "keys.json"]:
    if os.path.exists(f):
        os.remove(f)

# Inicializamos (asegúrate de que tu Rust genere las keys si no existen, o genéralas antes)
# Nota: payload y rules se enviaban como json strings o dicts? En lib.rs pusimos &str
# El usuario provee dicts en su script ("payload = {'accion': 'lectura', 'sensor': i}")
# Así que hay que convertirlos a JSON si el binding espera &str
db = TempusDDB("tmb_live_1234567890abcdefghij", "benchmark.db", "keys.json")

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

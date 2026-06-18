import subprocess
import json
import time
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_PATH = os.path.join(BASE_DIR, "target", "debug", "tempus-ddb")
KEY_FILE = "actor_keys.json"
DB_FILE = "tempus_ddb.db"

def run_cmd(args):
    """Ejecuta un comando del core en Rust e imprime la salida."""
    cmd = [BIN_PATH] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"❌ Error ejecutando {' '.join(args)}:\n{result.stderr}")
    return result.stdout.strip()

print("🚀 Iniciando prueba de la Decision Database (Tempus DDB)...\n")

# Limpieza inicial para garantizar un entorno fresco
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

# 1. Inicializar Base de Datos y Claves
print("1️⃣ Inicializando esquema SQLite y generando claves Ed25519...")
run_cmd(["init"])
run_cmd(["gen-keys", "--output", KEY_FILE])
print("   ✅ Base de datos lista y claves generadas.\n")

# 2. Registrar Evento Génesis (El inicio de la cadena)
print("2️⃣ Registrando Evento Génesis...")
payload_gen = json.dumps({"accion": "inicio_sistema", "modulo": "bot_principal"})
rules_gen = json.dumps({"version": "v1.0", "auth": "root"})
run_cmd(["record", "--payload", payload_gen, "--rules", rules_gen, "--keyfile", KEY_FILE, "--genesis"])
print("   ✅ Bloque Génesis sellado criptográficamente.\n")

time.sleep(1) # Pequeña pausa para simular paso del tiempo

# 3. Registrar Evento Subsecuente (Atado al Génesis)
print("3️⃣ Registrando Decisión 1 (Encadenada al Génesis)...")
payload_1 = json.dumps({"accion": "publicar_tweet", "contenido": "Hola Mundo Automatizado"})
rules_1 = json.dumps({"umbral_confianza": 0.95})
# Nota: Quitamos la flag --genesis para que Rust busque el hash anterior y lo enlace automáticamente
run_cmd(["record", "--payload", payload_1, "--rules", rules_1, "--keyfile", KEY_FILE])
print("   ✅ Decisión 1 sellada y encadenada.\n")

time.sleep(1)

# 4. Registrar Segundo Evento
print("4️⃣ Registrando Decisión 2 (Encadenada a la Decisión 1)...")
payload_2 = json.dumps({"accion": "compra_api", "monto": 15.50, "moneda": "USD"})
rules_2 = json.dumps({"saldo_suficiente": True})
run_cmd(["record", "--payload", payload_2, "--rules", rules_2, "--keyfile", KEY_FILE])
print("   ✅ Decisión 2 sellada y encadenada.\n")

# 5. Validar la Integridad Causal
print("5️⃣ Escaneando y validando la cadena criptográfica completa...")
validacion = run_cmd(["validate"])
print(f"   🔍 Resultado del Validador Rust:\n   {validacion}\n")
if not validacion:
    raise ValueError("❌ Expected validation output but got empty string.")

# 6. Exportar a JSON (Preparación para la nube)
print("6️⃣ Exportando Ledger a JSON para futura sincronización...")
exportacion = run_cmd(["export"])
print(f"   📦 Primeros caracteres del JSON exportado: {exportacion[:100]}...\n")
if not exportacion.startswith("[") and not exportacion.startswith("{"):
    raise ValueError("❌ Expected JSON export output, got invalid format.")

print("🎉 Prueba finalizada con éxito.")

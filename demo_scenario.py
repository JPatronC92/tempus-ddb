import json
import time
import os
import tempfile
from tempus_ddb import TempusDDB
import tempus_ddb

def main():
    print("🚀 Iniciando prueba de la Decision Database (Tempus DDB)...\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = os.path.join(tmpdir, "tempus.db")
        key_file = os.path.join(tmpdir, "actor_keys.json")

        # 1. Inicializar Base de Datos y Claves
        print("1️⃣ Inicializando esquema SQLite y generando claves Ed25519...")
        tempus_ddb.gen_keys(key_file)
        db = TempusDDB(db_file, key_file)
        print("   ✅ Base de datos lista y claves generadas.\n")

        # 2. Registrar Evento Génesis (El inicio de la cadena)
        print("2️⃣ Registrando Evento Génesis...")
        payload_gen = json.dumps({"accion": "inicio_sistema", "modulo": "bot_principal"})
        rules_gen = json.dumps({"version": "v1.0", "auth": "root"})
        
        result_gen = db.record(payload_gen, rules_gen, genesis=True)
        print(f"   ✅ Bloque Génesis sellado criptográficamente: {json.loads(result_gen).get('latest_hash')}\n")

        time.sleep(0.5) # Pequeña pausa para simular paso del tiempo

        # 3. Registrar Evento Subsecuente (Atado al Génesis)
        print("3️⃣ Registrando Decisión 1 (Encadenada al Génesis)...")
        payload_1 = json.dumps({"accion": "publicar_tweet", "contenido": "Hola Mundo Automatizado"})
        rules_1 = json.dumps({"umbral_confianza": 0.95})
        
        result_1 = db.record(payload_1, rules_1, genesis=False)
        print(f"   ✅ Decisión 1 sellada y encadenada: {json.loads(result_1).get('latest_hash')}\n")

        time.sleep(0.5)

        # 4. Registrar Segundo Evento
        print("4️⃣ Registrando Decisión 2 (Encadenada a la Decisión 1)...")
        payload_2 = json.dumps({"accion": "compra_api", "monto": 15.50, "moneda": "USD"})
        rules_2 = json.dumps({"saldo_suficiente": True})
        
        result_2 = db.record(payload_2, rules_2, genesis=False)
        print(f"   ✅ Decisión 2 sellada y encadenada: {json.loads(result_2).get('latest_hash')}\n")

        # 5. Validar la Integridad Causal
        print("5️⃣ Escaneando y validando la cadena criptográfica completa...")
        validacion = db.validate()
        print(f"   🔍 Resultado del Validador:\n   {validacion}\n")
        
        val_str = str(validacion).lower()
        if "invalid" in val_str or "error" in val_str:
            raise ValueError("❌ Expected validation to pass but it failed.")

        # 6. Exportar a JSON (Preparación para la nube)
        print("6️⃣ Exportando Ledger a JSON para futura sincronización...")
        exportacion = db.export()
        print(f"   📦 Primeros caracteres del JSON exportado: {exportacion[:100]}...\n")
        
        if not exportacion.startswith("[") and not exportacion.startswith("{"):
            raise ValueError("❌ Expected JSON export output, got invalid format.")

        print("🎉 Prueba finalizada con éxito.")

        del db
        import gc
        gc.collect()

if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

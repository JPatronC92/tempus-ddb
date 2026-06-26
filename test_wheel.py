from tempus_ddb import TempusDDB

print("🚀 SDK Tempus DDB: Prueba PyO3 Nativa\n")

try:
    # 1. Instanciamos la clase de Rust directamente en Python
    print("--- TEST 1: Sin gate de licencia ---")
    
    import tempus_ddb
    import os
    if not os.path.exists("keys.json"):
        tempus_ddb.gen_keys("keys.json")
        
    db = TempusDDB(
        db_path="flight_recorder.db", 
        keyfile="keys.json"
    )
    
    # Invocamos el motor de Rust
    receipt = db.record(payload='{"accion": "compra"}', rules='{"limite": 10}', genesis=True)
    print(f"✅ Motor Rust ejecutado con éxito: {receipt}\n")

except Exception as e:
    print(f"❌ Error: {e}")

import argparse
import json
import os
import tempfile
import time

import tempus_ddb
from tempus_ddb import TempusDDB


def run_benchmark(records: int, json_output: bool):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "benchmark.db")
        keys_path = os.path.join(tmpdir, "keys.json")

        tempus_ddb.gen_keys(keys_path)
        db = TempusDDB(db_path, keys_path)

        if not json_output:
            print(f"🔥 Iniciando benchmark de {records} decisiones inmutables...")
        
        start_time = time.time()

        batch = []
        for i in range(records):
            payload = json.dumps({"accion": "lectura", "sensor": i})
            rules = json.dumps({"limite": 100})
            batch.append((payload, rules))

        db.record_batch(batch, genesis=True)

        end_time = time.time()
        
        # Validation phase
        val_start = time.time()
        val_result = db.validate()
        val_end = time.time()
        
        duracion = end_time - start_time
        val_duracion = val_end - val_start
        
        # Verify validation actually passed
        val_str = str(val_result).lower()
        is_valid = "invalid" not in val_str and "error" not in val_str

        if json_output:
            print(json.dumps({
                "records": records,
                "duration_seconds": duracion,
                "throughput_per_sec": records / duracion if duracion > 0 else 0,
                "validation_duration_seconds": val_duracion,
                "is_valid": is_valid
            }))
        else:
            print(f"✅ {records} registros procesados y sellados criptográficamente.")
            print(f"⏱️ Tiempo de inserción: {duracion:.2f} segundos.")
            print(f"🚀 Velocidad: {records / duracion:.2f} decisiones por segundo.")
            print(f"🔍 Tiempo de validación: {val_duracion:.2f} segundos (Válido: {is_valid}).")

        del db
        import gc
        gc.collect()

if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Tempus DDB Benchmark")
    parser.add_argument("--records", type=int, default=1000, help="Number of records to benchmark")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()
    
    run_benchmark(args.records, args.json)

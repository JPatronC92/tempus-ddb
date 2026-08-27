import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN_PATH = os.path.join(PROJECT_DIR, "target", "debug", "tempus-ddb.exe") if os.name == 'nt' else os.path.join(PROJECT_DIR, "target", "debug", "tempus-ddb")

def build_rust_cli():
    print("Building Rust CLI...")
    result = subprocess.run(["cargo", "build"], cwd=PROJECT_DIR, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"Cargo build failed:\n{result.stderr}")
    print("Build successful.")

def run_cmd(*args):
    result = subprocess.run([BIN_PATH] + list(args), capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(args)}\nError: {result.stderr}\nStdout: {result.stdout}")
    return result.stdout.strip()

def main():
    build_rust_cli()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "stress_test.db")
        key_file = os.path.join(tmpdir, "stress_keys.json")
        
        print("\n==================================================")
        print("1. Initialize Database & Generate Keys...")
        
        run_cmd("init", "--db", db_path)
        run_cmd("gen-keys", "--output", key_file)
        print("Keys and DB created successfully.\n")
        
        print("2. Recording 50 sequential valid decisions...")
        start_time = time.time()
        for i in range(50):
            payload = json.dumps({"action": "sensor_read", "iteration": i, "value": i * 10.5})
            rules = json.dumps({"version": "v1.0.0"})
            
            args = ["record", "--db", db_path, "--payload", payload, "--rules", rules, "--keyfile", key_file]
            if i == 0:
                args.append("--genesis")
            
            run_cmd(*args)
            
        duration = time.time() - start_time
        print(f"Recorded 50 decisions in {duration:.2f} seconds.\n")
        
        print("3. Validating the clean causal chain...")
        val_result = run_cmd("validate", "--db", db_path)
        print("Validation Result:")
        print(val_result)
        print()
        
        print("4. Tampering with the database (Simulating data manipulation)...")
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, payload FROM decisions WHERE causal_depth = 25")
            row = cursor.fetchone()
            original_id, original_payload = row
            new_payload = json.dumps({"action": "sensor_read", "iteration": 25, "value": 99999.9}) # Malicious modification
            cursor.execute("UPDATE decisions SET payload = ? WHERE id = ?", (new_payload, original_id))
            conn.commit()
        finally:
            conn.close()
        
        print("Malicious update executed on depth 25.")
        print(f"Old payload: {original_payload}")
        print(f"New payload: {new_payload}\n")
        
        print("5. Re-validating the causal chain after tampering...")
        result = subprocess.run([BIN_PATH, "validate", "--db", db_path], capture_output=True, text=True, encoding="utf-8")
        print("Validation Output:")
        print(result.stdout)
        if result.returncode != 0:
            print("==================================================")
            print("SUCCESS: The system successfully detected the tampering and invalidated the chain!")
            print("==================================================")
        else:
            print("FAIL: The tampering was not detected.")
            sys.exit(1)

if __name__ == "__main__":
    main()

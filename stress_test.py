import subprocess
import json
import sqlite3
import time
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_PATH = os.path.join(BASE_DIR, "target", "debug", "tempus-ddb")
DB_PATH = os.path.join(BASE_DIR, "stress_test.db")
KEY_FILE = os.path.join(BASE_DIR, "stress_keys.json")

def run_cmd(*args):
    result = subprocess.run([BIN_PATH] + list(args), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(args)}\nError: {result.stderr}")
    return result.stdout.strip()

print("==================================================")
print("1. Initialize Database & Generate Keys...")
for f in [DB_PATH, KEY_FILE]:
    if os.path.exists(f):
        os.remove(f)

run_cmd("init", "--db", DB_PATH)
run_cmd("gen-keys", "--output", KEY_FILE)
print("Keys and DB created successfully.\n")

print("2. Recording 50 sequential valid decisions...")
start_time = time.time()
for i in range(50):
    payload = json.dumps({"action": "sensor_read", "iteration": i, "value": i * 10.5})
    rules = json.dumps({"version": "v1.0.0"})
    
    args = ["record", "--db", DB_PATH, "--payload", payload, "--rules", rules, "--keyfile", KEY_FILE]
    if i == 0:
        args.append("--genesis")
    
    run_cmd(*args)
    
duration = time.time() - start_time
print(f"Recorded 50 decisions in {duration:.2f} seconds.\n")

print("3. Validating the clean causal chain...")
val_result = run_cmd("validate", "--db", DB_PATH)
print("Validation Result:")
print(val_result)
print()

print("4. Tampering with the database (Simulating data manipulation)...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT id, payload FROM decisions WHERE causal_depth = 25")
row = cursor.fetchone()
original_id, original_payload = row
new_payload = json.dumps({"action": "sensor_read", "iteration": 25, "value": 99999.9}) # Malicious modification
cursor.execute("UPDATE decisions SET payload = ? WHERE id = ?", (new_payload, original_id))
conn.commit()
conn.close()

print(f"Malicious update executed on depth 25.")
print(f"Old payload: {original_payload}")
print(f"New payload: {new_payload}\n")

print("5. Re-validating the causal chain after tampering...")
result = subprocess.run([BIN_PATH, "validate", "--db", DB_PATH], capture_output=True, text=True)
print("Validation Output:")
print(result.stdout)
if result.returncode != 0:
    print("==================================================")
    print("SUCCESS: The system successfully detected the tampering and invalidated the chain!")
    print("==================================================")
else:
    print("FAIL: The tampering was not detected.")

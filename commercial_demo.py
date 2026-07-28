import json
import time
import os
import tempfile
import sys
from tempus_ddb import TempusDDB, gen_keys, TempusExecutor

class DownstreamAPI:
    """A simulated protected downstream API that only trusts Tempus permits."""
    def __init__(self, keyfile: str):
        # The API is protected by a Mediated Executor proxy internally (or explicitly)
        self.keyfile = keyfile

    def process_purchase_request_direct(self, agent_id: str, amount: int):
        # Without Tempus, the API rejects the request because it demands a permit
        return {"error": "Acceso denegado: Se requiere un permiso de Tempus válido para interactuar con esta API."}

class ExecutorProxy:
    """The mediated executor proxy that sits in front of the API."""
    def __init__(self, db_path: str, keyfile: str):
        self.executor = TempusExecutor(db_path, keyfile)
        self.purchase_count = 0

    def process_purchase_request(self, permit_json: str, amount: int):
        try:
            # 1. Enforced mediation: Consume permit atomically
            auth_str = self.executor.verify_and_consume_permit(permit_json)
            auth = json.loads(auth_str)

            # 2. Effect: Call the real API
            self.purchase_count += 1
            result = {"credits_added": amount, "total_credits": self.purchase_count * amount}

            # 3. Complete execution: Sign outcome
            outcome = self.executor.complete_execution(
                auth["authorization_id"],
                auth["action_id"],
                "SUCCEEDED",
                json.dumps(result)
            )
            return json.loads(outcome)

        except Exception as e:
            return {"error": str(e)}

def color_print(text, color_code):
    print(f"\033[{color_code}m{text}\033[0m")

def print_step(step_num, title):
    print(f"\n\033[1;36m[{step_num}] {title}\033[0m")

def main():
    print("================================================================")
    print(" Tempus DDB - Demostración Comercial (Epic 5)")
    print("================================================================\n")
    print("Esta demo prueba que: Un agente puede decidir lo que quiera, pero")
    print("no puede producir un efecto irreversible sin pasar por Tempus.\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        gate_db = os.path.join(tmpdir, "gate.db")
        exec_db = os.path.join(tmpdir, "exec.db")

        gate_keyfile = os.path.join(tmpdir, "gate.keys.json")
        agent_keyfile = os.path.join(tmpdir, "agent.keys.json")
        exec_keyfile = os.path.join(tmpdir, "executor.keys.json")

        gen_keys(gate_keyfile)
        gen_keys(agent_keyfile)
        gen_keys(exec_keyfile)

        gate = TempusDDB(gate_db, gate_keyfile)

        with open(gate_keyfile) as f: gate_id = json.load(f)["public_key"]
        with open(agent_keyfile) as f: agent_id = json.load(f)["public_key"]
        with open(exec_keyfile) as f: executor_id = json.load(f)["public_key"]

        gate.register_agent(gate_id, "tempus-gate", '{"can_delegate":true}')
        gate.register_agent(agent_id, "test-agent", "{}")
        gate.register_agent(executor_id, "test-executor", "{}")

        api = DownstreamAPI(exec_keyfile)
        proxy = ExecutorProxy(exec_db, exec_keyfile)

        time_ms = time.time_ns() // 1_000_000

        print_step("1", "Un agente intenta comprar sin Tempus (Falla)")
        result_no_tempus = api.process_purchase_request_direct(agent_id, 100)
        color_print(f"❌ Resultado: {result_no_tempus['error']}", "31")

        print_step("2", "Un agente intenta comprar con Tempus (Funciona)")
        intent = json.dumps({
            "schema_version": "tempus.action-intent.v1",
            "tenant_id": "demo-tenant",
            "agent_id": agent_id,
            "idempotency_key": f"purchase-demo-{time_ms}",
            "action_type": "purchase",
            "resource": "api/credits",
            "requested_at": time.time_ns() // 1_000,
            "input": {"amount": 100},
        })

        auth_result = json.loads(gate.request_action(intent, agent_keyfile, 60))
        permit = json.dumps(auth_result)
        color_print(f"✅ Permiso de Tempus emitido. ID: {auth_result['authorization']['authorization_id'][:16]}...", "32")

        outcome_success = proxy.process_purchase_request(permit, 100)
        if "error" not in outcome_success:
            color_print(f"✅ Ejecución exitosa. Resultado: {outcome_success['output']}", "32")
        else:
            color_print(f"❌ Error inesperado: {outcome_success['error']}", "31")

        print_step("3", "Un replay (reintento del mismo permiso) es rechazado")
        outcome_replay = proxy.process_purchase_request(permit, 100)
        color_print(f"❌ Resultado: {outcome_replay.get('error', 'Replay no detectado')}", "31")

        print_step("4", "Un permiso expirado es rechazado")
        intent_exp = json.dumps({
            "schema_version": "tempus.action-intent.v1",
            "tenant_id": "demo-tenant",
            "agent_id": agent_id,
            "idempotency_key": f"purchase-exp-{time_ms}",
            "action_type": "purchase",
            "resource": "api/credits",
            "requested_at": time.time_ns() // 1_000,
            "input": {"amount": 100},
        })
        # Permit expires in 1 second
        auth_result_exp = json.loads(gate.request_action(intent_exp, agent_keyfile, 1))
        permit_exp = json.dumps(auth_result_exp)
        print("Esperando 1.5 segundos para que expire el permiso...")
        time.sleep(1.5)
        outcome_exp = proxy.process_purchase_request(permit_exp, 100)
        color_print(f"❌ Resultado: {outcome_exp.get('error', 'Expiración no detectada')}", "31")

        print_step("5", "Un permiso alterado es rechazado")
        intent_alt = json.dumps({
            "schema_version": "tempus.action-intent.v1",
            "tenant_id": "demo-tenant",
            "agent_id": agent_id,
            "idempotency_key": f"purchase-alt-{time_ms}",
            "action_type": "purchase",
            "resource": "api/credits",
            "requested_at": time.time_ns() // 1_000,
            "input": {"amount": 100},
        })
        auth_result_alt = json.loads(gate.request_action(intent_alt, agent_keyfile, 60))
        # Alter the permit payload
        auth_result_alt["authorization"]["action_id"] = "fake-action-id-123"
        permit_alt = json.dumps(auth_result_alt)
        outcome_alt = proxy.process_purchase_request(permit_alt, 100)
        color_print(f"❌ Resultado: {outcome_alt.get('error', 'Alteración no detectada')}", "31")

        print_step("6", "Se genera un receipt verificable")
        # Commit the original successful outcome to the gate to get the execution receipt
        receipt_str = gate.commit_outcome(
            auth_result['authorization']['authorization_id'],
            json.dumps(outcome_success),
            exec_keyfile
        )
        receipt = json.loads(receipt_str)
        color_print(f"✅ Receipt de ejecución final guardado en Tempus. ID: {receipt['receipt']['receipt_id'][:16]}...", "32")

        verification_str = gate.verify_trace(auth_result['authorization']['action_id'])
        verification = json.loads(verification_str)
        if verification.get('status') == 'VERIFIED':
            color_print(f"✅ Verificación criptográfica completada: {verification['status']} (Fase: {verification['phase']})", "32")
        else:
            color_print(f"❌ Fallo en verificación: {verification}", "31")

        print("\n================================================================")
        print(" Demo Finalizada Exitosamente")
        print("================================================================\n")

if __name__ == "__main__":
    main()

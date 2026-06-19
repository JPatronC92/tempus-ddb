import asyncio
import json
import os
import sys
import io
import sqlite3
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Force stdout to use utf-8 to prevent UnicodeEncodeError on Windows
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ── Files for the demo ──
DB_PATH = "b2a_agent.db"
KEY_PATH = "b2a_keys.json"
WALLET_FILE = "agent_wallet.json"
SECRET_KEY_FILE = "server_secret.key"

def cleanup():
    """Clean up old workspace database, keys and wallet files."""
    for path in [DB_PATH, KEY_PATH, WALLET_FILE, SECRET_KEY_FILE]:
        if os.path.exists(path):
            os.remove(path)

async def run_b2a_agent_demo():
    print("======================================================================")
    print(">>> INICIANDO DEMO MVP HARDENED DE TEMPUS DDB (Modelo B2A Avanzado)")
    print("======================================================================\n")

    cleanup()

    # Configuration for launching the local stdio MCP server using sys.executable
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server.py"],
        env=os.environ.copy()
    )

    print("[CONN] Conectando al Servidor MCP de Tempus DDB...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("[CONN] Conexion establecida con exito.\n")

            # ── 1. Inicialización de la Base de Datos y Claves ──
            print("[DB] [Paso 1] Inicializando base de datos Tempus DDB...")
            init_res = await session.call_tool("tempus_init", arguments={"db": DB_PATH})
            print(f"[MCP] {init_res.content[0].text}\n")

            print("[KEYS] [Paso 2] Generando claves criptograficas para el agente...")
            keys_res = await session.call_tool("tempus_gen_keys", arguments={"output": KEY_PATH})
            print(f"[MCP] {keys_res.content[0].text}\n")

            # ── 2. Prueba de Aislamiento de Múltiples Agentes (Task 5 / Task 1) ──
            print("[AISLAMIENTO] [Paso 3] Verificando aislamiento de multiples agentes...")
            agent_alice = "agent_alice"
            agent_bob = "agent_bob"

            # Alice se fondea con 1.0 USDC, Bob permanece en 0.0 USDC
            print(f"[WALLET] Fondeando a {agent_alice} con 1.0 USDC...")
            await session.call_tool("tempus_fund_wallet", arguments={"agent_id": agent_alice, "amount": 1.0})
            
            # Consultar balances de ambos
            bal_alice_res = await session.call_tool("tempus_check_balance", arguments={"agent_id": agent_alice})
            bal_bob_res = await session.call_tool("tempus_check_balance", arguments={"agent_id": agent_bob})
            
            alice_data = json.loads(bal_alice_res.content[0].text)
            bob_data = json.loads(bal_bob_res.content[0].text)
            print(f"[OK] Balance de Alice: {alice_data['balance_usdc']} USDC")
            print(f"[OK] Balance de Bob: {bob_data['balance_usdc']} USDC")
            assert alice_data['balance_usdc'] == 1.0, "Alice deberia tener 1.0 USDC"
            assert bob_data['balance_usdc'] == 0.0, "Bob deberia tener 0.0 USDC"
            print("   => Aislamiento de saldos verificado correctamente.\n")

            # ── 3. Prueba de Idempotencia y Reintentos (Task 2 / Task 5) ──
            print("[IDEMPOTENCIA] [Paso 4] Registrando decision con idempotency_key...")
            payload = json.dumps({"action": "execute_trade", "token": "SOL", "amount": 10})
            rules = json.dumps({"price_slippage": 0.02})
            ikey = "idempotency_key_trade_999"

            # Primera ejecucion (debe cobrar y registrar exitosamente)
            record_res = await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH,
                "payload": payload,
                "rules": rules,
                "keyfile": KEY_PATH,
                "genesis": True,
                "agent_id": agent_alice,
                "idempotency_key": ikey
            })
            record_data = json.loads(record_res.content[0].text)
            print(f"[MCP] Balance de Alice tras primer registro: {record_data['remaining_balance_usdc']} USDC")
            assert record_data['remaining_balance_usdc'] == 0.99, "Deberia haber cobrado 0.01 USDC"
            genesis_hash = record_data["output"]["latest_hash"]

            # Segunda ejecucion (reintento del agente con misma idempotency_key)
            print("[IDEMPOTENCIA] Agente reintenta misma llamada con la misma idempotency_key...")
            record_res_retry = await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH,
                "payload": payload,
                "rules": rules,
                "keyfile": KEY_PATH,
                "genesis": True,
                "agent_id": agent_alice,
                "idempotency_key": ikey
            })
            retry_data = json.loads(record_res_retry.content[0].text)
            print(f"[MCP] Balance de Alice tras reintento: {retry_data['remaining_balance_usdc']} USDC")
            assert retry_data['remaining_balance_usdc'] == 0.99, "No deberia haber vuelto a cobrar saldo"
            assert retry_data["output"]["latest_hash"] == genesis_hash, "El hash de la respuesta debe ser idéntico"
            print("   => Idempotencia verificada: el reintento devolvio el cache exitosamente sin cobro doble.\n")

            # ── 4. Decisiones Diferentes Sí Cobran (Task 5) ──
            print("[RECORD] [Paso 5] Registrando una segunda decision diferente...")
            payload_2 = json.dumps({"action": "execute_trade", "token": "BTC", "amount": 0.05})
            ikey_2 = "idempotency_key_trade_1000"

            record_res_2 = await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH,
                "payload": payload_2,
                "rules": rules,
                "keyfile": KEY_PATH,
                "parent": genesis_hash,
                "genesis": False,
                "agent_id": agent_alice,
                "idempotency_key": ikey_2
            })
            record_data_2 = json.loads(record_res_2.content[0].text)
            print(f"[MCP] Balance de Alice tras segunda decision: {record_data_2['remaining_balance_usdc']} USDC")
            assert record_data_2['remaining_balance_usdc'] == 0.98, "Deberia haber cobrado otros 0.01 USDC"
            print("   => Decisiones distintas cobran saldo correctamente.\n")

            # ── 5. Reversion / Reembolso ante Fallos del Ledger (Task 3 / Task 5) ──
            print("[ROLLBACK] [Paso 6] Simulando un error en el motor Rust para verificar reembolso...")
            # Forzamos un fallo intentando registrar un segundo bloque Genesis (prohibido por el core)
            print(f"Saldo actual antes de la falla: {record_data_2['remaining_balance_usdc']} USDC")
            
            fail_res = await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH,
                "payload": payload,
                "rules": rules,
                "keyfile": KEY_PATH,
                "genesis": True,  # Duplicado de Genesis (fallara)
                "agent_id": agent_alice,
                "idempotency_key": "idempotency_genesis_fail"
            })
            fail_data = json.loads(fail_res.content[0].text)
            print(f"[MCP] Error recibido: {fail_data['error']}")
            
            # Verificar balance tras el fallo. Debe ser idéntico al anterior (0.98) por el reembolso.
            bal_check = await session.call_tool("tempus_check_balance", arguments={"agent_id": agent_alice})
            bal_check_data = json.loads(bal_check.content[0].text)
            print(f"Saldo actual despues de la falla: {bal_check_data['balance_usdc']} USDC")
            assert bal_check_data['balance_usdc'] == 0.98, "El cobro de la transaccion fallida debio ser reembolsado"
            print("   => Reversion transaccional (reserve -> record [fail] -> refund) verificada correctamente.\n")

            # ── 6. Inspección de Eventos Económicos Locales (Task 4 / Task 5) ──
            print("[AUDIT] [Paso 7] Inspeccionando eventos economicos locales registrados...")
            print(f"Eventos economicos de {agent_alice}:")
            for e in bal_check_data["economic_events"]:
                print(f"  * Tipo: {e['type']} | Monto: {e['amount']} | Motivo: {e['reason']}")
            print("   => Registro de eventos economicos verificado.\n")

            # ── 7. Prueba de Detección de Manipulación en Wallet (Task 5) ──
            print("[SEGURIDAD] [Paso 8] Simulando manipulacion manual fraudulenta de wallet...")
            with open(WALLET_FILE, "r") as f:
                w_data = json.load(f)
            # Modificar balance de Alice directamente en el archivo sin actualizar HMAC
            w_data["agents"]["agent_alice"]["balance_usdc"] = 9999.0
            with open(WALLET_FILE, "w") as f:
                json.dump(w_data, f, indent=2)
            print("   [!] Wallet alterada directamente en disco (Alice balance = 9999.0).")
            
            # Intentar verificar balance o usar wallet. Debe fallar por HMAC inválido.
            try:
                tamper_res = await session.call_tool("tempus_check_balance", arguments={"agent_id": agent_alice})
                tamper_data = json.loads(tamper_res.content[0].text)
                print(f"[MCP] {json.dumps(tamper_data, indent=2)}")
                if tamper_data.get("status") == "error":
                    print("✅ [OK] El sistema rechazo operar debido a la manipulacion del wallet.")
                else:
                    print("❌ [Fallo] El sistema permitio operar con un wallet manipulado.")
            except Exception as exc:
                print(f"✅ [OK] El sistema lanzo excepcion e impidio operar: {exc}")
            print()

            # Restauramos archivos para validación de SQLite
            cleanup()
            print("[SEGURIDAD] Re-inicializando base de datos limpia para validacion causal...")
            await session.call_tool("tempus_init", arguments={"db": DB_PATH})
            await session.call_tool("tempus_gen_keys", arguments={"output": KEY_PATH})
            await session.call_tool("tempus_fund_wallet", arguments={"agent_id": agent_alice, "amount": 1.0})
            
            # Registrar genesis limpio
            rec_genesis = await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH, "payload": payload, "rules": rules, "keyfile": KEY_PATH, "genesis": True, "agent_id": agent_alice
            })
            genesis_res_data = json.loads(rec_genesis.content[0].text)
            g_hash = genesis_res_data["output"]["latest_hash"]

            # ── 8. Prueba de Detección de Manipulación en SQLite (Task 5) ──
            print("[SEGURIDAD] [Paso 9] Simulando manipulacion manual en base de datos SQLite...")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE decisions SET payload = '{\"action\": \"corrupted_action\"}' WHERE causal_depth = 0")
            conn.commit()
            conn.close()
            print("   [!] SQLite manipulado directamente (payload de Genesis modificado).")

            # Validar causalidad
            val_res = await session.call_tool("tempus_validate", arguments={"db": DB_PATH})
            val_data = json.loads(val_res.content[0].text)
            print(f"[MCP] {json.dumps(val_data, indent=2)}\n")
            
            val_text = str(val_data.get("result", val_data.get("message", ""))).lower()
            if "invalid" in val_text or "error" in val_text or "mismatch" in val_text:
                print("[ALERT] [Agente / Sistema]: ALERT! Se detecto manipulacion del Ledger.")
                print("[STOP] [Agente]: Deteniendo operaciones (Criterio de Seguridad cumplido con exito).\n")
            else:
                print("❌ [Fallo]: La manipulacion del Ledger no fue detectada.\n")

if __name__ == "__main__":
    asyncio.run(run_b2a_agent_demo())

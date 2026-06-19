import asyncio
import json
import os
import sys
import io
import sqlite3
import unittest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Force stdout to use utf-8 to prevent UnicodeEncodeError on Windows
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_PATH = "test_b2a.db"
KEY_PATH = "test_keys.json"
WALLET_FILE = "agent_wallet.json"
SECRET_KEY_FILE = "server_secret.key"

def cleanup():
    for f in [DB_PATH, KEY_PATH, WALLET_FILE, SECRET_KEY_FILE]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except OSError:
                pass

class TestB2ALocal(unittest.IsolatedAsyncioTestCase):
    async def run_with_session(self, test_func):
        cleanup()
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["mcp_server.py"],
            env=os.environ.copy()
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await session.call_tool("tempus_init", arguments={"db": DB_PATH})
                await session.call_tool("tempus_gen_keys", arguments={"output": KEY_PATH})
                await test_func(session)
        cleanup()

    async def test_insufficient_funds_json(self):
        async def inner(session):
            payload = json.dumps({"action": "test"})
            rules = json.dumps({})
            res = await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH, "payload": payload, "rules": rules, "keyfile": KEY_PATH,
                "genesis": True, "agent_id": "poor_agent", "idempotency_key": "key1"
            })
            data = json.loads(res.content[0].text)
            self.assertEqual(data.get("status"), "error")
            self.assertEqual(data.get("error"), "TEMPUS_INSUFFICIENT_FUNDS")
            self.assertEqual(data.get("error_code"), "insufficient_funds")
            self.assertIn("next_action", data)
            self.assertEqual(data["next_action"], "tempus_fund_wallet")
        await self.run_with_session(inner)

    async def test_fund_wallet_isolation(self):
        async def inner(session):
            await session.call_tool("tempus_fund_wallet", arguments={"agent_id": "agent_a", "amount": 1.0})
            res_a = await session.call_tool("tempus_check_balance", arguments={"agent_id": "agent_a"})
            data_a = json.loads(res_a.content[0].text)
            self.assertEqual(data_a["balance_usdc"], 1.0)
            
            res_b = await session.call_tool("tempus_check_balance", arguments={"agent_id": "agent_b"})
            data_b = json.loads(res_b.content[0].text)
            self.assertEqual(data_b["balance_usdc"], 0.0)
        await self.run_with_session(inner)

    async def test_reserve_commit_success(self):
        async def inner(session):
            await session.call_tool("tempus_fund_wallet", arguments={"agent_id": "agent_x", "amount": 1.0})
            payload = json.dumps({"action": "test"})
            rules = json.dumps({})
            res = await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH, "payload": payload, "rules": rules, "keyfile": KEY_PATH,
                "genesis": True, "agent_id": "agent_x", "idempotency_key": "key_success"
            })
            data = json.loads(res.content[0].text)
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["remaining_balance_usdc"], 0.99)
            
            res_bal = await session.call_tool("tempus_check_balance", arguments={"agent_id": "agent_x"})
            bal_data = json.loads(res_bal.content[0].text)
            self.assertEqual(bal_data["balance_usdc"], 0.99)
        await self.run_with_session(inner)

    async def test_reserve_refund_failure(self):
        async def inner(session):
            await session.call_tool("tempus_fund_wallet", arguments={"agent_id": "agent_fail", "amount": 1.0})
            payload = json.dumps({"action": "test"})
            rules = json.dumps({})
            
            await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH, "payload": payload, "rules": rules, "keyfile": KEY_PATH,
                "genesis": True, "agent_id": "agent_fail", "idempotency_key": "key_fail_1"
            })
            
            res = await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH, "payload": payload, "rules": rules, "keyfile": KEY_PATH,
                "genesis": True, "agent_id": "agent_fail", "idempotency_key": "key_fail_2"
            })
            data = json.loads(res.content[0].text)
            self.assertEqual(data["status"], "error")
            
            res_bal = await session.call_tool("tempus_check_balance", arguments={"agent_id": "agent_fail"})
            bal_data = json.loads(res_bal.content[0].text)
            self.assertEqual(bal_data["balance_usdc"], 0.99)
        await self.run_with_session(inner)

    async def test_idempotency_key(self):
        async def inner(session):
            await session.call_tool("tempus_fund_wallet", arguments={"agent_id": "agent_idem", "amount": 1.0})
            payload = json.dumps({"action": "test"})
            rules = json.dumps({})
            
            res1 = await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH, "payload": payload, "rules": rules, "keyfile": KEY_PATH,
                "genesis": True, "agent_id": "agent_idem", "idempotency_key": "idem_key"
            })
            data1 = json.loads(res1.content[0].text)
            
            res2 = await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH, "payload": payload, "rules": rules, "keyfile": KEY_PATH,
                "genesis": True, "agent_id": "agent_idem", "idempotency_key": "idem_key"
            })
            data2 = json.loads(res2.content[0].text)
            
            self.assertEqual(data1, data2)
            
            res_bal = await session.call_tool("tempus_check_balance", arguments={"agent_id": "agent_idem"})
            bal_data = json.loads(res_bal.content[0].text)
            self.assertEqual(bal_data["balance_usdc"], 0.99)
        await self.run_with_session(inner)

    async def test_different_idempotency_keys(self):
        async def inner(session):
            await session.call_tool("tempus_fund_wallet", arguments={"agent_id": "agent_diff", "amount": 1.0})
            payload = json.dumps({"action": "test"})
            rules = json.dumps({})
            
            res1 = await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH, "payload": payload, "rules": rules, "keyfile": KEY_PATH,
                "genesis": True, "agent_id": "agent_diff", "idempotency_key": "diff_key_1"
            })
            data1 = json.loads(res1.content[0].text)
            hash1 = data1["output"]["latest_hash"]
            
            res2 = await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH, "payload": json.dumps({"action": "test2"}), "rules": rules, "keyfile": KEY_PATH,
                "parent": hash1, "genesis": False, "agent_id": "agent_diff", "idempotency_key": "diff_key_2"
            })
            
            res_bal = await session.call_tool("tempus_check_balance", arguments={"agent_id": "agent_diff"})
            bal_data = json.loads(res_bal.content[0].text)
            self.assertEqual(bal_data["balance_usdc"], 0.98)
        await self.run_with_session(inner)

    async def test_wallet_tampering(self):
        async def inner(session):
            await session.call_tool("tempus_fund_wallet", arguments={"agent_id": "agent_tamp", "amount": 1.0})
            
            with open(WALLET_FILE, "r") as f:
                w = json.load(f)
            w["agents"]["agent_tamp"]["balance_usdc"] = 999.0
            with open(WALLET_FILE, "w") as f:
                json.dump(w, f)
                
            res = await session.call_tool("tempus_check_balance", arguments={"agent_id": "agent_tamp"})
            data = json.loads(res.content[0].text)
            self.assertEqual(data["status"], "error")
            self.assertIn("tampered", data["message"].lower())
        await self.run_with_session(inner)

    async def test_ledger_tampering(self):
        async def inner(session):
            await session.call_tool("tempus_fund_wallet", arguments={"agent_id": "agent_ledg", "amount": 1.0})
            payload = json.dumps({"action": "test"})
            rules = json.dumps({})
            await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH, "payload": payload, "rules": rules, "keyfile": KEY_PATH,
                "genesis": True, "agent_id": "agent_ledg", "idempotency_key": "ledg_key"
            })
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("UPDATE decisions SET payload = 'corrupted' WHERE causal_depth = 0")
            conn.commit()
            conn.close()
            
            res = await session.call_tool("tempus_validate", arguments={"db": DB_PATH})
            data = json.loads(res.content[0].text)
            self.assertEqual(data["status"], "error")
            self.assertEqual(data["error"], "TEMPUS_LEDGER_INTEGRITY_FAILURE")
        await self.run_with_session(inner)

    async def test_commit_failure_reconciliation(self):
        async def inner(session):
            await session.call_tool("tempus_fund_wallet", arguments={"agent_id": "agent_rec", "amount": 1.0})
            payload = json.dumps({"action": "test"})
            rules = json.dumps({})
            
            with open(WALLET_FILE, "r") as f:
                w = json.load(f)
            # Add an agent state with PENDING_COMMIT directly
            w["agents"]["agent_rec"] = {
                "balance_usdc": 0.99,
                "reserved_balance_usdc": 0.01,
                "economic_events": [],
                "idempotency_keys": {
                    "rec_key": {
                        "status": "PENDING_COMMIT",
                        "cost_incurred_usdc": 0.01,
                        "output": {"latest_hash": "simulated_hash"}
                    }
                }
            }
            # Compute new hmac!
            import hmac, hashlib, json as j
            with open(SECRET_KEY_FILE, "rb") as fk:
                secret = fk.read()
            c_data = {}
            for aid, info in sorted(w["agents"].items()):
                c_data[aid] = {
                    "balance_usdc": float(info["balance_usdc"]),
                    "reserved_balance_usdc": float(info.get("reserved_balance_usdc", 0.0)),
                    "economic_events": info.get("economic_events", []),
                    "idempotency_keys": info.get("idempotency_keys", {})
                }
            msg = j.dumps(c_data, sort_keys=True).encode()
            w["hmac"] = hmac.new(secret, msg, hashlib.sha256).hexdigest()
            with open(WALLET_FILE, "w") as f:
                json.dump(w, f)
            
            # Now retry with rec_key
            res = await session.call_tool("tempus_record_decision", arguments={
                "db": DB_PATH, "payload": payload, "rules": rules, "keyfile": KEY_PATH,
                "genesis": True, "agent_id": "agent_rec", "idempotency_key": "rec_key"
            })
            data = json.loads(res.content[0].text)
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["remaining_balance_usdc"], 0.99)
            
            res_bal = await session.call_tool("tempus_check_balance", arguments={"agent_id": "agent_rec"})
            bal_data = json.loads(res_bal.content[0].text)
            self.assertEqual(bal_data["balance_usdc"], 0.99)
            self.assertEqual(bal_data["reserved_balance_usdc"], 0.0)
            
        await self.run_with_session(inner)

if __name__ == "__main__":
    unittest.main()

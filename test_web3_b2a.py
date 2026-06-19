import unittest
import json
import os
import sys
from unittest.mock import patch
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
import tempus_ddb.web3_adapter

# Ensure environment is properly mocked for tests
os.environ["TEMPUS_MODE"] = "web3-testnet"
os.environ["TEMPUS_TREASURY_ADDRESS"] = "0x695512626414AcA9cFA1b955A19056Dd974091C0"

class TestWeb3B2A(unittest.IsolatedAsyncioTestCase):
    async def run_with_session(self, func):
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "tempus_ddb.mcp_server"],
            env=os.environ.copy()
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Run the inner test block
                await func(session)

    @patch("tempus_ddb.web3_adapter.Web3PaymentAdapter.verify_funding_tx")
    async def test_web3_funding_flow(self, mock_verify):
        # 0.0001 ETH * 3000 = 0.30 credits
        mock_verify.return_value = 0.30

        async def inner(session):
            # 1. Provide a mock tx_hash to fund the wallet
            tx_hash = "0x123abcmocktransactionhash"
            res = await session.call_tool("tempus_fund_wallet", arguments={
                "agent_id": "web3_agent",
                "tx_hash": tx_hash,
                "network": "base-sepolia"
            })
            data = json.loads(res.content[0].text)
            if data["status"] != "success":
                print(f"ERROR: {data}")
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["funded_amount_usdc"], 0.30)
            
            # 2. Anti-Replay mechanism: prevent double spending the same tx_hash
            res_replay = await session.call_tool("tempus_fund_wallet", arguments={
                "agent_id": "web3_agent",
                "tx_hash": tx_hash,
                "network": "base-sepolia"
            })
            data_replay = json.loads(res_replay.content[0].text)
            self.assertEqual(data_replay["status"], "error")
            self.assertIn("TEMPUS_DUPLICATE_FUNDING_TX", data_replay["message"])

            # 3. Prove that we can use the web3 funds to actually record a causal decision
            res_rec = await session.call_tool("tempus_record", arguments={
                "db": "web3_test.db",
                "payload": json.dumps({"test": "web3_purchase"}),
                "rules": "{}",
                "keyfile": "keys.json",
                "genesis": True,
                "agent_id": "web3_agent"
            })
            rec_data = json.loads(res_rec.content[0].text)
            self.assertEqual(rec_data["status"], "success")
            # 0.30 - 0.01 = 0.29
            self.assertEqual(rec_data["remaining_balance_usdc"], 0.29)
            
        await self.run_with_session(inner)

if __name__ == "__main__":
    unittest.main()

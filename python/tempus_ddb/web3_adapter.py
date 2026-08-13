import os

from web3 import AsyncWeb3, Web3

NETWORKS = {
    "base-sepolia": "https://sepolia.base.org"
}

# Mock exchange rate for MVP
ETH_TO_USDC_RATE = 3000.0

class Web3PaymentAdapter:
    def __init__(self):
        self.treasury_address = os.environ.get("TEMPUS_TREASURY_ADDRESS")
        if not self.treasury_address:
            raise RuntimeError("TEMPUS_TREASURY_ADDRESS is not set in the environment.")
        self.treasury_address = Web3.to_checksum_address(self.treasury_address)

    async def verify_funding_tx(self, network: str, tx_hash: str) -> float:
        """
        Verifies the transaction on the given network.
        Returns the equivalent USDC amount based on the ETH sent.
        """
        if network not in NETWORKS:
            raise ValueError(f"TEMPUS_INVALID_NETWORK: Supported networks are {list(NETWORKS.keys())}")
            
        w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(NETWORKS[network]))
        
        try:
            tx = await w3.eth.get_transaction(tx_hash)
            receipt = await w3.eth.get_transaction_receipt(tx_hash)
        except Exception as e:
            raise ValueError(f"TEMPUS_TX_VERIFICATION_FAILED: Could not fetch transaction. {e!s}")

        if receipt["status"] != 1:
            raise ValueError("TEMPUS_TX_FAILED: Transaction reverted on-chain.")
            
        if not tx["to"] or tx["to"].lower() != self.treasury_address.lower():
            raise ValueError("TEMPUS_TX_INVALID_RECIPIENT: Transaction was not sent to the Tempus Treasury Wallet.")

        eth_amount = float(w3.from_wei(tx["value"], 'ether'))
        if eth_amount <= 0:
            raise ValueError("TEMPUS_TX_INVALID_AMOUNT: Transaction value is 0.")

        # Convert to equivalent credits
        equivalent_usdc = eth_amount * ETH_TO_USDC_RATE
        return equivalent_usdc

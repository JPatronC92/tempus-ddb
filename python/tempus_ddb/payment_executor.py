"""Credential-isolated Financial / Payment executor for Tempus permits."""

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional, Protocol

from ._tempus_ddb import TempusExecutor


class PaymentExecutorError(RuntimeError):
    """Base error for financial executor failures."""


class PaymentTransport(Protocol):
    """Transport protocol for financial transactions."""

    def disburse(
        self, secret_key: str, amount: str, asset: str, beneficiary: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute one mediated payout."""


class MockPaymentTransport:
    """Deterministic payment transport with isolated credentials."""

    def disburse(
        self, secret_key: str, amount: str, asset: str, beneficiary: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not secret_key:
            raise PaymentExecutorError("Payment provider secret key is missing")
        # In real deployments, calls Stripe/Wise/Banking APIs with the isolated secret key
        tx_id = f"tx_mock_{os.urandom(8).hex()}"
        return {
            "status": "SETTLED",
            "transaction_id": tx_id,
            "amount": amount,
            "asset": asset,
            "beneficiary": beneficiary,
            "metadata": metadata,
        }


class PaymentExecutorAdapter:
    """Mediated executor that enforces financial limits and isolates payout secrets."""

    SUPPORTED_ACTIONS = {"finance.disburse", "finance.transfer", "payment.charge"}

    def __init__(
        self,
        executor_db: str,
        executor_keyfile: str,
        trusted_gate_id: str,
        trusted_tenant_id: str,
        secret_key: Optional[str] = None,
        transport: Optional[PaymentTransport] = None,
        executor_pool_size: int = 8,
    ):
        self._executor = TempusExecutor(
            executor_db,
            executor_keyfile,
            trusted_gate_id,
            trusted_tenant_id,
            executor_pool_size,
        )
        self._secret_key = secret_key or os.environ.get("PAYMENT_SECRET_KEY", "default-isolated-payment-key")
        self._transport = transport or MockPaymentTransport()

    def execute(self, permit_json: str) -> str:
        """Verify, enforce money envelope, execute payout, and sign outcome."""
        auth_response = json.loads(permit_json)
        intent = auth_response.get("intent") or auth_response.get("authorization", {}).get("intent", {})

        action_type = intent.get("action_type")
        if action_type not in self.SUPPORTED_ACTIONS:
            raise PaymentExecutorError(f"Unsupported financial action type: {action_type}")

        # Enforce presence of universal money envelope
        money = intent.get("money")
        if not money or not isinstance(money, dict):
            raise PaymentExecutorError("Financial action requires a valid 'money' envelope in intent")

        amount = str(money.get("amount", ""))
        asset = str(money.get("asset", ""))
        beneficiary = str(money.get("beneficiary", ""))

        if not amount or not asset or not beneficiary:
            raise PaymentExecutorError("Missing 'amount', 'asset', or 'beneficiary' in money metadata")

        # 1. Enforce atomic single consumption
        consumed_auth_str = self._executor.verify_and_consume_permit(permit_json)
        consumed_auth = json.loads(consumed_auth_str)
        auth_id = consumed_auth["authorization_id"]
        action_id = consumed_auth["action_id"]

        input_data = intent.get("input", {})

        # 2. Perform financial effect with isolated key
        try:
            payout_result = self._transport.disburse(
                self._secret_key, amount, asset, beneficiary, input_data
            )
            status = "SUCCEEDED"
            output_payload = payout_result
        except Exception as exc:
            status = "FAILED"
            output_payload = {"error": str(exc)}

        # 3. Sign and emit receipt
        return self._executor.complete_execution(
            auth_id,
            action_id,
            status,
            json.dumps(output_payload),
        )

    execute_permit = execute


def main() -> None:
    parser = argparse.ArgumentParser(description="Tempus Credential-Isolated Payment Executor")
    parser.add_argument("--permit", required=True, help="Path to permit JSON file")
    parser.add_argument("--executor-db", required=True, help="Path to executor SQLite DB")
    parser.add_argument("--executor-keyfile", required=True, help="Path to executor keys JSON")
    parser.add_argument("--gate-id", required=True, help="Trusted Tempus Gate public key")
    parser.add_argument("--tenant-id", required=True, help="Expected tenant ID")
    parser.add_argument("--secret-key", help="Optional PAYMENT_SECRET_KEY")
    parser.add_argument("--executor-pool-size", type=int, default=8, help="Connection pool size")

    args = parser.parse_args()

    with open(args.permit, "r", encoding="utf-8") as f:
        permit_content = f.read()

    adapter = PaymentExecutorAdapter(
        executor_db=args.executor_db,
        executor_keyfile=args.executor_keyfile,
        trusted_gate_id=args.gate_id,
        trusted_tenant_id=args.tenant_id,
        secret_key=args.secret_key,
        executor_pool_size=args.executor_pool_size,
    )

    try:
        receipt = adapter.execute_permit(permit_content)
        print(receipt)
    except Exception as exc:
        print(f"Execution failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

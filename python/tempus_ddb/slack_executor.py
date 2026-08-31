"""Credential-isolated Slack executor for Tempus permits."""

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional, Protocol
from urllib import error, request

from . import __version__
from ._tempus_ddb import TempusExecutor


class SlackExecutorError(RuntimeError):
    """Base error for Slack executor failures."""


class SlackTransport(Protocol):
    """Transport protocol for Slack API requests."""

    def request(
        self, endpoint: str, token: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute one Slack API call."""


class UrllibSlackTransport:
    """Builtin HTTPS Slack transport."""

    def request(
        self, endpoint: str, token: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        url = f"https://slack.com/api/{endpoint.lstrip('/')}"
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
            "User-Agent": f"Tempus-Slack-Executor/{__version__}",
        }
        req = request.Request(url, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=30) as response:  # nosec B310
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw)
                if not parsed.get("ok", False):
                    raise SlackExecutorError(f"Slack API error: {parsed.get('error', 'unknown')}")
                return parsed
        except error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise SlackExecutorError(f"Slack HTTP error {exc.code}: {err_body}") from exc
        except Exception as exc:
            raise SlackExecutorError(f"Slack transport failed: {exc}") from exc


class SlackExecutorAdapter:
    """Mediated executor for Slack notifications and alerts."""

    SUPPORTED_ACTIONS = {"slack.post_message", "slack.send_alert"}

    def __init__(
        self,
        executor_db: str,
        executor_keyfile: str,
        trusted_gate_id: str,
        trusted_tenant_id: str,
        token: Optional[str] = None,
        transport: Optional[SlackTransport] = None,
        executor_pool_size: int = 8,
    ):
        self._executor = TempusExecutor(
            executor_db,
            executor_keyfile,
            trusted_gate_id,
            trusted_tenant_id,
            executor_pool_size,
        )
        self._token = token or os.environ.get("SLACK_BOT_TOKEN")
        self._transport = transport or UrllibSlackTransport()

    def execute(self, permit_json: str) -> str:
        """Verify permit, post to Slack with isolated token, and sign outcome."""
        if not self._token:
            raise SlackExecutorError("SLACK_BOT_TOKEN must be provided to the executor")

        auth_response = json.loads(permit_json)
        intent = auth_response.get("intent") or auth_response.get("authorization", {}).get("intent", {})

        action_type = intent.get("action_type")
        if action_type not in self.SUPPORTED_ACTIONS:
            raise SlackExecutorError(f"Unsupported action type: {action_type}")

        channel = intent.get("resource")
        input_data = intent.get("input", {})
        text = input_data.get("text") or input_data.get("message")
        if not text:
            raise SlackExecutorError("Missing 'text' or 'message' field in input")

        # 1. Enforce atomic single consumption
        consumed_auth_str = self._executor.verify_and_consume_permit(permit_json)
        consumed_auth = json.loads(consumed_auth_str)
        auth_id = consumed_auth["authorization_id"]
        action_id = consumed_auth["action_id"]

        slack_payload = {
            "channel": channel,
            "text": text,
        }
        if "blocks" in input_data:
            slack_payload["blocks"] = input_data["blocks"]

        # 2. Perform external effect with isolated token
        try:
            res = self._transport.request("chat.postMessage", self._token, slack_payload)
            status = "SUCCEEDED"
            output_payload = {"channel": channel, "ts": res.get("ts"), "message_id": res.get("message", {}).get("ts")}
        except Exception as exc:
            status = "FAILED"
            output_payload = {"error": str(exc)}

        # 3. Sign outcome
        return self._executor.complete_execution(
            auth_id,
            action_id,
            status,
            json.dumps(output_payload),
        )

    execute_permit = execute


def main() -> None:
    parser = argparse.ArgumentParser(description="Tempus Credential-Isolated Slack Executor")
    parser.add_argument("--permit", required=True, help="Path to permit JSON file")
    parser.add_argument("--executor-db", required=True, help="Path to executor SQLite DB")
    parser.add_argument("--executor-keyfile", required=True, help="Path to executor keys JSON")
    parser.add_argument("--gate-id", required=True, help="Trusted Tempus Gate public key")
    parser.add_argument("--tenant-id", required=True, help="Expected tenant ID")
    parser.add_argument("--token", help="Optional SLACK_BOT_TOKEN")
    parser.add_argument("--executor-pool-size", type=int, default=8, help="Connection pool size")

    args = parser.parse_args()

    with open(args.permit, "r", encoding="utf-8") as f:
        permit_content = f.read()

    adapter = SlackExecutorAdapter(
        executor_db=args.executor_db,
        executor_keyfile=args.executor_keyfile,
        trusted_gate_id=args.gate_id,
        trusted_tenant_id=args.tenant_id,
        token=args.token,
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

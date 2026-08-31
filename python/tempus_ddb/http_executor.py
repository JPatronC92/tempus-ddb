"""Credential-isolated HTTP/Webhook executor for Tempus permits."""

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional, Protocol
from urllib import error, parse, request

from . import __version__
from ._tempus_ddb import TempusExecutor


class HttpExecutorError(RuntimeError):
    """Base error for HTTP executor failures."""


class HttpAPIError(HttpExecutorError):
    """A non-2xx HTTP response from the target endpoint."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


class UnknownExecutionError(HttpExecutorError):
    """Outcome is ambiguous; must not be automatically retried."""

    def __init__(self, observation: str):
        super().__init__("HTTP execution outcome is UNKNOWN")
        self.observation = observation


def _validate_https_url(target_url: str) -> str:
    candidate = target_url.strip()
    parsed = parse.urlsplit(candidate)
    if parsed.scheme != "https" or not parsed.netloc:
        raise HttpExecutorError("Target URL must be a valid HTTPS endpoint")
    return candidate


class HttpTransport(Protocol):
    """Transport protocol for mockability and real requests."""

    def request(
        self, method: str, url: str, headers: Dict[str, str], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute one HTTP request."""


class UrllibHttpTransport:
    """Builtin HTTPS transport with zero external dependencies."""

    def request(
        self, method: str, url: str, headers: Dict[str, str], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        _validate_https_url(url)
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8") if payload else None
        req = request.Request(url, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=30) as response:  # nosec B310
                raw = response.read().decode("utf-8")
                try:
                    return json.loads(raw) if raw else {"status": "ok", "http_status": response.status}
                except json.JSONDecodeError:
                    return {"body": raw, "http_status": response.status}
        except error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise HttpAPIError(exc.code, f"HTTP {exc.code}: {err_body}") from exc
        except Exception as exc:
            raise HttpExecutorError(f"HTTP transport failed: {exc}") from exc


class HttpExecutorAdapter:
    """Mediated executor that executes HTTPS POST/PUT webhooks with isolated credentials."""

    SUPPORTED_ACTIONS = {"http.post", "http.put", "webhook.send"}

    def __init__(
        self,
        executor_db: str,
        executor_keyfile: str,
        trusted_gate_id: str,
        trusted_tenant_id: str,
        auth_header: Optional[str] = None,
        transport: Optional[HttpTransport] = None,
        executor_pool_size: int = 8,
    ):
        self._executor = TempusExecutor(
            executor_db,
            executor_keyfile,
            trusted_gate_id,
            trusted_tenant_id,
            executor_pool_size,
        )
        self._auth_header = auth_header or os.environ.get("HTTP_EXECUTOR_AUTH_HEADER")
        self._transport = transport or UrllibHttpTransport()

    def execute(self, permit_json: str) -> str:
        """Verify, consume, execute, and sign the outcome receipt."""
        auth_response = json.loads(permit_json)
        intent = auth_response.get("intent") or auth_response.get("authorization", {}).get("intent", {})

        action_type = intent.get("action_type")
        if action_type not in self.SUPPORTED_ACTIONS:
            raise HttpExecutorError(f"Unsupported action type: {action_type}")

        target_url = intent.get("resource")
        _validate_https_url(target_url)

        input_data = intent.get("input", {})
        method = "PUT" if action_type == "http.put" else "POST"

        # 1. Enforce atomic single consumption
        consumed_auth_str = self._executor.verify_and_consume_permit(permit_json)
        consumed_auth = json.loads(consumed_auth_str)
        auth_id = consumed_auth["authorization_id"]
        action_id = consumed_auth["action_id"]

        # 2. Prepare headers with isolated credentials
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"Tempus-Http-Executor/{__version__}",
        }
        if self._auth_header:
            headers["Authorization"] = self._auth_header

        # 3. Perform effect with isolated key
        try:
            result = self._transport.request(method, target_url, headers, input_data)
            status = "SUCCEEDED"
            output_payload = result
        except HttpAPIError as exc:
            status = "FAILED"
            output_payload = {"error": str(exc), "status_code": exc.status_code}
        except Exception as exc:
            status = "FAILED"
            output_payload = {"error": str(exc)}

        # 4. Sign and emit outcome receipt
        return self._executor.complete_execution(
            auth_id,
            action_id,
            status,
            json.dumps(output_payload),
        )

    execute_permit = execute


def main() -> None:
    parser = argparse.ArgumentParser(description="Tempus Credential-Isolated HTTP Executor")
    parser.add_argument("--permit", required=True, help="Path to permit JSON file")
    parser.add_argument("--executor-db", required=True, help="Path to executor SQLite DB")
    parser.add_argument("--executor-keyfile", required=True, help="Path to executor keys JSON")
    parser.add_argument("--gate-id", required=True, help="Trusted Tempus Gate public key")
    parser.add_argument("--tenant-id", required=True, help="Expected tenant ID")
    parser.add_argument("--auth-header", help="Optional secret Authorization header")
    parser.add_argument("--executor-pool-size", type=int, default=8, help="Connection pool size")

    args = parser.parse_args()

    with open(args.permit, "r", encoding="utf-8") as f:
        permit_content = f.read()

    adapter = HttpExecutorAdapter(
        executor_db=args.executor_db,
        executor_keyfile=args.executor_keyfile,
        trusted_gate_id=args.gate_id,
        trusted_tenant_id=args.tenant_id,
        auth_header=args.auth_header,
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

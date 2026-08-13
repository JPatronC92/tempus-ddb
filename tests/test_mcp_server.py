import json
import time

import pytest
import tempus_ddb.mcp_server as mcp_module
from tempus_ddb.mcp_server import call_tool, list_tools, validate_path


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(mcp_module, "SANDBOX_DIR", str(tmp_path))
    monkeypatch.setattr(mcp_module, "TEMPUS_GATE_KEYFILE", "keys.json")
    monkeypatch.setattr(mcp_module, "TEMPUS_ADMIN_TOOLS", False)
    monkeypatch.setattr(mcp_module, "TEMPUS_LEGACY_TOOLS", False)
    monkeypatch.setattr(mcp_module, "TEMPUS_DESTRUCTIVE_TOOLS", False)
    return tmp_path


@pytest.mark.asyncio
async def test_default_tool_surface_is_b2a_and_fail_closed(sandbox):
    tools = await list_tools()
    names = {tool.name for tool in tools}
    assert {
        "tempus_request_action",
        "tempus_commit_outcome",
        "tempus_get_trace",
        "tempus_verify_trace",
        "tempus_list_agents",
    } <= names
    assert "tempus_record" not in names
    assert "tempus_register_agent" not in names
    assert "tempus_cleanup" not in names

    response = await call_tool("tempus_record", {})
    payload = json.loads(response[0].text)
    assert payload["status"] == "error"
    assert payload["error"] == "TEMPUS_LEGACY_TOOL_DISABLED"


def test_validate_path(sandbox):
    valid = validate_path("test.db")
    assert valid.startswith(str(sandbox))
    assert valid.endswith("test.db")
    with pytest.raises(ValueError, match="Path escapes sandbox|disallowed '\\.\\.'"):
        validate_path("../outside.db")


@pytest.mark.asyncio
async def test_mcp_b2a_workflow(sandbox, monkeypatch):
    monkeypatch.setattr(mcp_module, "TEMPUS_ADMIN_TOOLS", True)

    for output in ["keys.json", "agent.keys.json", "executor.keys.json"]:
        response = await call_tool("tempus_gen_keys", {"output": output})
        assert json.loads(response[0].text)["status"] == "success"
    response = await call_tool("tempus_init", {"db": "test.db"})
    assert json.loads(response[0].text)["status"] == "success"

    agent_id = json.loads((sandbox / "agent.keys.json").read_text())["public_key"]
    executor_id = json.loads((sandbox / "executor.keys.json").read_text())["public_key"]
    for public_key, alias in [
        (agent_id, "buyer-agent"),
        (executor_id, "purchase-executor"),
    ]:
        response = await call_tool(
            "tempus_register_agent",
            {"db": "test.db", "public_key": public_key, "alias": alias},
        )
        assert json.loads(response[0].text)["status"] == "success"

    intent = json.dumps({
        "schema_version": "tempus.action-intent.v1",
        "tenant_id": "mcp-test",
        "agent_id": agent_id,
        "idempotency_key": "mcp-action-001",
        "action_type": "deploy",
        "resource": "service/api",
        "requested_at": time.time_ns() // 1_000,
        "input": {"version": "1.2.3"},
    })
    response = await call_tool(
        "tempus_request_action",
        {
            "db": "test.db",
            "intent": intent,
            "agent_keyfile": "agent.keys.json",
        },
    )
    authorization = json.loads(response[0].text)
    assert authorization["authorization"]["decision"] == "ALLOWED"
    authorization_id = authorization["authorization"]["authorization_id"]
    action_id = authorization["authorization"]["action_id"]

    outcome = json.dumps({
        "schema_version": "tempus.action-outcome.v1",
        "authorization_id": authorization_id,
        "action_id": action_id,
        "status": "SUCCEEDED",
        "external_reference": "deploy-9182",
    })
    response = await call_tool(
        "tempus_commit_outcome",
        {
            "db": "test.db",
            "authorization_id": authorization_id,
            "outcome": outcome,
            "executor_keyfile": "executor.keys.json",
        },
    )
    assert json.loads(response[0].text)["receipt"]["status"] == "SUCCEEDED"

    response = await call_tool(
        "tempus_verify_trace",
        {"db": "test.db", "action_id": action_id},
    )
    verification = json.loads(response[0].text)
    assert verification["status"] == "VERIFIED"
    assert verification["phase"] == "COMPLETED"

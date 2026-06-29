import pytest
import json
import os
import tempfile
from tempus_ddb.mcp_server import call_tool, list_tools, validate_path, app

@pytest.fixture
def sandbox():
    # Setup a temporary directory as the sandbox for tests
    with tempfile.TemporaryDirectory() as tmpdir:
        import tempus_ddb.mcp_server as mcp_module
        old_sandbox = mcp_module.SANDBOX_DIR
        mcp_module.SANDBOX_DIR = tmpdir
        yield tmpdir
        mcp_module.SANDBOX_DIR = old_sandbox

@pytest.mark.asyncio
async def test_list_tools():
    tools = await list_tools()
    names = [t.name for t in tools]
    assert "tempus_init" in names
    assert "tempus_gen_keys" in names
    assert "tempus_record" in names
    assert "tempus_validate" in names
    assert "tempus_cleanup" in names

def test_validate_path(sandbox):
    # Should resolve correctly
    valid = validate_path("test.db")
    assert valid.startswith(sandbox)
    assert valid.endswith("test.db")
    
    # Path traversal should fail
    with pytest.raises(ValueError, match="Path escapes sandbox|disallowed '\\.\\.'"):
        validate_path("../outside.db")

@pytest.mark.asyncio
async def test_mcp_workflow(sandbox):
    # 1. Gen Keys
    result = await call_tool("tempus_gen_keys", {"output": "keys.json"})
    assert "status" in result[0].text
    resp = json.loads(result[0].text)
    assert resp["status"] == "success"
    assert "keys.json" in resp["key_file"]

    # 2. Init
    result = await call_tool("tempus_init", {"db": "test.db"})
    resp = json.loads(result[0].text)
    assert resp["status"] == "success"

    # 3. Record (Genesis)
    result = await call_tool("tempus_record", {
        "db": "test.db",
        "payload": '{"action": "test"}',
        "rules": '{"rule": "1"}',
        "keyfile": "keys.json",
        "genesis": True
    })
    resp = json.loads(result[0].text)
    assert resp["status"] == "success"

    # 4. Record (Child)
    result = await call_tool("tempus_record", {
        "db": "test.db",
        "payload": '{"action": "test2"}',
        "rules": '{"rule": "2"}',
        "keyfile": "keys.json",
        "genesis": False
    })
    resp = json.loads(result[0].text)
    assert resp["status"] == "success"

    # 5. Validate
    result = await call_tool("tempus_validate", {"db": "test.db"})
    resp = json.loads(result[0].text)
    assert resp["status"] == "success"

    # 6. Invalid Payload
    result = await call_tool("tempus_record", {
        "db": "test.db",
        "payload": 'invalid json',
        "rules": '{"rule": "2"}',
        "keyfile": "keys.json"
    })
    resp = json.loads(result[0].text)
    assert resp["status"] == "error"
    assert "TEMPUS_EXECUTION_ERROR" in resp["error"]
    assert "valid JSON string" in resp["message"]

    # 7. Cleanup
    result = await call_tool("tempus_cleanup", {})
    resp = json.loads(result[0].text)
    assert resp["status"] == "success"
    assert len(resp["removed"]) > 0

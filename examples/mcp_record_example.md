# Using Tempus DDB with MCP

The default MCP server is an autonomous B2A gate, not a legacy decision recorder. It
never accepts an agent or executor private-key path. The requesting agent signs the
canonical intent locally, and the executor signs the outcome locally.

1. Install and configure the server:

```json
{
  "mcpServers": {
    "tempus-ddb": {
      "command": "tempus",
      "args": ["mcp", "start"],
      "env": {
        "TEMPUS_MODE": "autonomous",
        "TEMPUS_GATE_KEYFILE": "keys.json"
      }
    }
  }
}
```

2. Provision the gate and register identities outside the agent-facing MCP process.
Use the CLI or a separately controlled process with `TEMPUS_ADMIN_TOOLS=1`.

3. An autonomous client uses these default tools:

- `tempus_request_action_signed`: submits `intent`, `agent_id`, and
  `agent_signature` to obtain a permit.
- `tempus_commit_outcome_signed`: submits an executor-signed outcome to consume a
  permit.
- `tempus_get_trace`, `tempus_verify_trace`, and `tempus_list_agents`: read-only
  evidence operations.

The legacy `record`, `validate`, and cleanup tools remain available only with their
explicit environment flags. Local keyfile B2A tools also require
`TEMPUS_LOCAL_KEYFILE_TOOLS=1` and are for development compatibility only.

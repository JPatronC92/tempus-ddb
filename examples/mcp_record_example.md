# Using Tempus DDB with MCP (e.g. Claude Desktop)

1. Make sure you have the package installed:
   ```bash
   pip install -e .
   ```

2. Add to your MCP client config (Claude, Cursor, etc.):

```json
{
  "mcpServers": {
    "tempus-ddb": {
      "command": "tempus",
      "args": ["mcp", "start"]
    }
  }
}
```

3. In your conversation with the agent, instruct it to use the tools:

Example prompt you can give the agent:

"You must use the tempus_init, tempus_gen_keys, and tempus_record_decision tools 
to record any important decision before executing it.

Example decision:
- payload: {\"action\": \"update_pricing\", \"old_price\": 99, \"new_price\": 129}
- rules: {\"max_change_percent\": 50, \"requires_review\": true}
- Use genesis=true for the first decision.

Always call tempus_validate after a few decisions to prove the chain is intact."

The agent will then call the MCP tools automatically.

## Available Tools

- tempus_init
- tempus_gen_keys  
- tempus_record / tempus_record_decision
- tempus_validate
- tempus_cleanup

See the main README for parameter details.
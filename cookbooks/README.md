# 📚 Tempus DDB Cookbooks & Integration Recipes

Practical, copy-paste recipes for integrating Tempus DDB B2A security gates into popular AI agent frameworks and LLM environments.

---

## 🍳 Available Recipes

| Recipe | Framework / Environment | Description |
|---|---|---|
| [**LangChain & LangGraph Guard**](langchain_agent_guard.py) | LangChain / LangGraph | Enforce zero-trust tool execution gates around sensitive actions (database writes, payouts, API calls). |
| [**CrewAI Financial Gate**](crewai_action_gate.py) | CrewAI / Multi-Agent Teams | Multi-agent delegation where executor agents only act when presented with a single-use gate permit. |
| [**Claude & Cursor MCP Guide**](mcp_cursor_claude_quickstart.md) | Claude Desktop / Cursor / Windsurf | Connect Tempus DDB as an autonomous Model Context Protocol server in 2 minutes. |

---

## ⚡ Quick Start

```bash
# 1. Install Tempus DDB
pip install tempus-ddb

# 2. Run the LangChain guard recipe
python cookbooks/langchain_agent_guard.py

# 3. Run the CrewAI financial gate recipe
python cookbooks/crewai_action_gate.py
```

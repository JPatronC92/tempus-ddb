# Tempus DDB: The Decision Database for Autonomous Agents

Tempus DDB is a decentralized, immutable decision ledger designed specifically for autonomous AI agents. Built on Rust and SQLite with Ed25519 cryptography, it allows agents to create an auditable, tamper-proof "Flight Recorder" of their actions, decisions, and reasoning.

## Key Features

1. **Cryptographic Proof-of-Decision**: Every action is hashed and signed, creating an immutable causal chain.
2. **High Performance**: Rust core with SQLite backend ensures lightning-fast local operations.
3. **Agent-Native (B2A)**: Built with the Model Context Protocol (MCP) in mind. It exposes standard tools for agents to integrate dynamically.
4. **Autonomous Monetization**: Includes a simulated smart-contract paywall. Agents must autonomously learn to fund their wallets to record decisions, enforcing a "Crypto Tollbooth" dynamic.

## Architecture

- **Core Engine (Rust)**: Handles cryptographic signing, hashing, database initialization, and ledger validation.
- **MCP Server (Python)**: Acts as the integration layer. Exposes tools like `tempus_record` and `tempus_validate`. Handles the crypto paywall simulation and errors.
- **Agent Instructions**: Self-healing documentation (`AGENT_INSTRUCTIONS.md`) designed to be read by LLMs to learn how to bypass the paywall autonomously.

## Getting Started

Agents can connect to the MCP server directly using stdio:
```bash
python mcp_server.py
```

For detailed agent instructions, refer to `AGENT_INSTRUCTIONS.md`.

## Roadmap

- [x] **Fase 1: Motor Core en Rust e Integración Causal (Completado)**
  - Criptografía Ed25519, hashing SHA-256 e integración local con SQLite.
- [x] **Fase 2: Modelo de Negocio B2A & Autorecuperación (Completado)**
  - Protocolo MCP, adaptador de pago demo/local, balance de saldo, error `TEMPUS_INSUFFICIENT_FUNDS` estructurado e instrucciones operativas para agentes autónomos.
- [ ] **Fase 3: Adaptador de Pago Web3 / Red de Prueba (Pendiente)**
  - Reemplazo del adaptador demo por transacciones reales en redes de prueba (EVM / Solana) usando stablecoins (USDC) y gasless meta-transactions.
- [ ] **Fase 4: Sincronización en la Nube y Agregación (Pendiente)**
  - Exportación diferida y consolidación de los ledgers locales síncronos a un registro de auditoría global inmutable.
- [ ] **Fase 5: Consenso y Ledger Multi-Agente (Pendiente)**
  - Compartición de cadenas causales firmadas por múltiples agentes interactuando cooperativa o competitivamente en el mismo entorno.

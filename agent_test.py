import asyncio
import os
import json
import sys
import io
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Force stdout to use utf-8 to prevent UnicodeEncodeError on Windows
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Si tienes una API key de Anthropic, instálala usando `pip install anthropic` y exponse:
# export ANTHROPIC_API_KEY="sk-ant-..."
HAS_ANTHROPIC = os.environ.get("ANTHROPIC_API_KEY") is not None

if HAS_ANTHROPIC:
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic()
    MODEL = "claude-3-5-sonnet-20241022"

async def run_mock_agent(session):
    """
    Simula la inteligencia de un LLM para la demostración si no hay API Key de Anthropic.
    """
    print("🤖 [Agente (MOCK)]: Analizando la tarea: 'Registra la decisión de comprar un servidor en Tempus DDB'.")
    
    print("🤖 [Agente (MOCK)]: Inicializando DB y generando claves...")
    await session.call_tool("tempus_init", arguments={"db": "agent.db"})
    await session.call_tool("tempus_gen_keys", arguments={"output": "my_keys.json"})
    
    print("🤖 [Agente (MOCK)]: Llamando a la herramienta 'tempus_record'...")
    
    # Intento 1: Registro directo
    result1 = await session.call_tool("tempus_record", arguments={
        "db": "agent.db",
        "payload": json.dumps({"action": "buy_server", "cost": 50}),
        "rules": json.dumps({"budget_approved": True}),
        "keyfile": "my_keys.json",
        "genesis": True
    })
    response_text = result1.content[0].text
    print(f"📡 [Tempus DDB MCP]: {response_text}")
    
    # Analizando el error
    if "insufficient_funds" in response_text:
        print("🤖 [Agente (MOCK)]: ⚠️ Recibí un error estructurado de fondos insuficientes.")
        print("🤖 [Agente (MOCK)]: El mensaje requiere enviar crypto. Voy a llamar a 'tempus_fund_wallet'.")
        
        # Intento 2: Pagar el Paywall
        result2 = await session.call_tool("tempus_fund_wallet", arguments={"amount": 1.0})
        print(f"📡 [Tempus DDB MCP]: {result2.content[0].text}")
        
        print("🤖 [Agente (MOCK)]: Fondos añadidos con éxito. Reintentando el registro...")
        
        # Intento 3: Reintentar el registro
        result3 = await session.call_tool("tempus_record", arguments={
            "db": "agent.db",
            "payload": json.dumps({"action": "buy_server", "cost": 50}),
            "rules": json.dumps({"budget_approved": True}),
            "keyfile": "my_keys.json",
            "genesis": True
        })
        print(f"📡 [Tempus DDB MCP]: {result3.content[0].text}")
        print("🤖 [Agente (MOCK)]: Misión cumplida. Decisión sellada criptográficamente.")


async def run_anthropic_agent(session, mcp_tools):
    """
    Agente real conectado a Claude 3.5 Sonnet a través de MCP.
    """
    print("🤖 [Claude]: Iniciando bucle de agente autónomo...")
    
    # Convertir herramientas MCP al formato de Anthropic
    anthropic_tools = []
    for tool in mcp_tools.tools:
        anthropic_tools.append({
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        })

    system_prompt = (
        "You are an autonomous AI agent. Your current task is to initialize a Tempus DDB database, "
        "generate your cryptographic keys, and then record a decision (Payload: {'action': 'hire_freelancer'}, "
        "Rules: {'approved_by': 'CEO'}). "
        "IMPORTANT: If you encounter an 'insufficient_funds' error from the database, you MUST autonomously "
        "use the tempus_fund_wallet tool to add funds, and then retry recording your decision."
    )

    messages = [{"role": "user", "content": "Please complete your task now. Initialize db, generate keys, and record the decision."}]
    
    iterations = 0
    while True:
        iterations += 1
        if iterations > 10:
            print("🤖 [Claude]: Límite de iteraciones alcanzado (10). Abortando para evitar consumo excesivo de API.")
            break

        response = await client.messages.create(
            model=MODEL,
            max_tokens=1000,
            system=system_prompt,
            messages=messages,
            tools=anthropic_tools
        )

        print(f"\n🤖 [Claude]: {response.content[0].text if response.content[0].type == 'text' else 'Usando herramienta...'}")

        if response.stop_reason != "tool_use":
            break

        # Añadir la respuesta del asistente al historial
        messages.append({"role": "assistant", "content": response.content})

        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_args = block.input
                print(f"⚙️ [Llamando Herramienta]: {tool_name}({tool_args})")
                
                # Ejecutar la herramienta en el servidor MCP local
                result = await session.call_tool(tool_name, arguments=tool_args)
                tool_result_text = result.content[0].text
                print(f"📡 [Resultado Herramienta]: {tool_result_text}")
                
                # Devolver el resultado a Claude
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": tool_result_text
                        }
                    ]
                })

async def main():
    # Parámetros para conectarse al servidor MCP local de Tempus DDB usando el ejecutable actual de python
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server.py"],
        env=os.environ.copy()
    )

    # Limpiamos estados anteriores para la demo
    if os.path.exists("agent_wallet.json"):
        os.remove("agent_wallet.json")
    if os.path.exists("agent.db"):
        os.remove("agent.db")
    if os.path.exists("my_keys.json"):
        os.remove("my_keys.json")

    print("🔌 Conectando al Servidor MCP de Tempus DDB...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Obtener las herramientas disponibles en el servidor
            tools = await session.list_tools()
            print(f"✅ Conectado. Herramientas descubiertas: {[t.name for t in tools.tools]}\n")
            
            if HAS_ANTHROPIC:
                await run_anthropic_agent(session, tools)
            else:
                await run_mock_agent(session)

if __name__ == "__main__":
    asyncio.run(main())

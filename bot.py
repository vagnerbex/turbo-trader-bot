import asyncio
import json
import threading
import time
import websocket
import websockets.server
import os
DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN", "pat_1a31318b45e8d24cba8c3b1c955e87dbd562fb57641564a25541e51c25e9151")

# Configurações da Deriv API
DERIV_WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"
MERCADOS = ["R_100", "R_75"]

CLIENTES_CONECTADOS = set()
DERIV_APP = None

def transmitir(mensagem):
    """Transmite dados para o painel web local (HTML/JS)."""
    msg_str = json.dumps(mensagem)
    for cliente in list(CLIENTES_CONECTADOS):
        try:
            asyncio.run_coroutine_threadsafe(cliente.send(msg_str), loop_principal)
        except Exception:
            CLIENTES_CONECTADOS.discard(cliente)

def enviar_ordem_deriv(dados):
    """Envia o comando de compra para os servidores da Deriv."""
    global DERIV_APP
    if not DERIV_APP or not DERIV_APP.sock or not DERIV_APP.sock.connected:
        print("⚠️ Conexão com a Deriv fechada. Não foi possível enviar a ordem.")
        return

    req_compra = {
        "buy": 1,
        "price": float(dados.get("stake", 1.0)),
        "parameters": {
            "amount": float(dados.get("stake", 1.0)),
            "basis": "stake",
            "contract_type": dados.get("direction", "CALL"),
            "currency": "USD",
            "duration": int(dados.get("duration", 5)),
            "duration_unit": "t",
            "symbol": dados.get("symbol", "R_100")
        }
    }
    print(f"🚀 Disparando ordem: {dados.get('direction')} | Stake: ${dados.get('stake')} | Ativo: {dados.get('symbol')}")
    DERIV_APP.send(json.dumps(req_compra))

def on_message(ws, message):
    dado = json.loads(message)
    if "authorize" in dado:
        saldo = dado["authorize"].get("balance", 0)
        print(f"💰 Conta Autenticada com sucesso | Saldo: ${float(saldo):.2f}")
        transmitir({
            "type": "sync_balance",
            "balance": f"${float(saldo):.2f}"
        })
    elif "tick" in dado:
        transmitir({
            "type": "tick",
            "symbol": dado["tick"]["symbol"],
            "quote": dado["tick"]["quote"]
        })
    elif "buy" in dado:
        print("✅ Ordem executada com sucesso na Deriv!")
        transmitir({
            "type": "order_result",
            "data": dado["buy"]
        })

def on_open(ws):
    print("✅ Conectado com sucesso à Deriv API!")
    if DERIV_API_TOKEN != "COLE_SEU_TOKEN_AQUI":
        print("🔑 Autenticando com o Token...")
        ws.send(json.dumps({"authorize": DERIV_API_TOKEN}))
    for sym in MERCADOS:
        ws.send(json.dumps({"ticks": sym, "subscribe": 1}))

def on_error(ws, error):
    print(f"⚠️ Erro na conexão Deriv: {error}")

def on_close(ws, close_status_code, close_msg):
    print("🔌 Conexão com a Deriv encerrada.")

def gerenciar_deriv():
    global DERIV_APP
    while True:
        print("⏳ Conectando aos servidores da Deriv...")
        websocket.enableTrace(False)
        
        # Cabeçalhos avançados para simular perfeitamente um navegador Google Chrome e evitar o Erro 520
        DERIV_APP = websocket.WebSocketApp(
            DERIV_WS_URL,
            header={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Origin": "https://app.deriv.com",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            },
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        import certifi
        import ssl
        DERIV_APP.run_forever(
            ping_interval=20,
            ping_timeout=10,
            sslopt={"ca_certs": certifi.where(), "cert_reqs": ssl.CERT_REQUIRED}
        )
        print("🔄 Tentando reconectar à Deriv em 3s...")
        time.sleep(3)

async def handler_cliente(websocket_local):
    CLIENTES_CONECTADOS.add(websocket_local)
    print("🔌 Painel Web conectado com sucesso!")
    try:
        async for mensagem in websocket_local:
            dados = json.loads(mensagem)
            if dados.get("action") == "buy":
                enviar_ordem_deriv(dados)
    except Exception as e:
        print(f"Desconexão de cliente web: {e}")
    finally:
        CLIENTES_CONECTADOS.discard(websocket_local)

loop_principal = None

async def main():
    global loop_principal
    loop_principal = asyncio.get_running_loop()
    
    # Inicia a gestão da Deriv numa thread em segundo plano
    threading.Thread(target=gerenciar_deriv, daemon=True).start()
    
    print("🤖 Servidor Local WebSocket iniciado em ws://0.0.0.0:8765")
    async with websockets.server.serve(handler_cliente, "0.0.0.0", 8765):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

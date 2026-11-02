// ==========================================
// 1. GERENCIADOR DE ESTADO (STATE)
// ==========================================
const STATE = {
  socket: null,
  activeSymbol: 'R_100',
  isExecutingTrade: false,
  reconnectInterval: 3000
};

// ==========================================
// 2. CONEXÃO WEBSOCKET COM bot.py
// ==========================================
function connectLocalBridge() {
  const badge = document.getElementById('connection-badge');
  console.log("Conectando à porta local ws://127.0.0.1:8765...");

  STATE.socket = new WebSocket('ws://127.0.0.1:8765');

  STATE.socket.onopen = () => {
    console.log("✅ Conectado ao bot.py!");
    if (badge) {
      badge.innerText = "Conectado via Python";
      badge.className = "badge badge-connected";
    }
  };

  STATE.socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      // Sincronização de Saldo
      if (data.type === 'sync_balance') {
        const balanceElem = document.getElementById('account-balance-val');
        if (balanceElem) balanceElem.innerText = data.balance;
      }

      // Cotação de Ticks em Tempo Real
      if (data.type === 'tick' && data.symbol === STATE.activeSymbol) {
        const priceElem = document.getElementById('price-base');
        if (priceElem) priceElem.innerText = Number(data.quote).toFixed(2);
      }

      // Retorno de Confirmação da Ordem
      if (data.type === 'order_result' || data.type === 'order_closed') {
        STATE.isExecutingTrade = false;
        console.log("Resultado da transação:", data);
      }
    } catch (error) {
      console.error("Erro ao processar mensagem:", error);
    }
  };

  STATE.socket.onclose = () => {
    console.warn("🔌 Conexão fechada. Reconectando em 3s...");
    if (badge) {
      badge.innerText = "Desconectado";
      badge.className = "badge badge-disconnected";
    }
    const priceElem = document.getElementById('price-base');
    if (priceElem) priceElem.innerText = "---";

    setTimeout(connectLocalBridge, STATE.reconnectInterval);
  };

  STATE.socket.onerror = (err) => {
    console.error("Erro no WebSocket local:", err);
  };
}

// ==========================================
// 3. ENVIO DE ORDENS DE COMPRA
// ==========================================
function sendBuyOrder(direction) {
  if (!STATE.socket || STATE.socket.readyState !== WebSocket.OPEN) {
    alert("O servidor bot.py não está ativo. Inicie o Python no terminal!");
    return;
  }

  if (STATE.isExecutingTrade) {
    console.warn("Aguarde a finalização da ordem em andamento.");
    return;
  }

  const stake = document.getElementById('order-stake')?.value || "1.00";
  const duration = document.getElementById('order-duration')?.value || "5";

  STATE.isExecutingTrade = true;

  const payload = {
    action: 'buy',
    direction: direction,
    stake: stake,
    duration: duration,
    duration_unit: 't',
    symbol: STATE.activeSymbol
  };

  STATE.socket.send(JSON.stringify(payload));
  console.log(`🚀 Ordem disparada (${direction}):`, payload);

  // Destrava de segurança por timeout (caso caia sinal)
  setTimeout(() => {
    STATE.isExecutingTrade = false;
  }, 10000);
}

// ==========================================
// 4. INICIALIZAÇÃO
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-buy-call')?.addEventListener('click', () => sendBuyOrder('CALL'));
  document.getElementById('btn-buy-put')?.addEventListener('click', () => sendBuyOrder('PUT'));

  document.getElementById('select-symbol')?.addEventListener('change', (e) => {
    STATE.activeSymbol = e.target.value;
    const priceElem = document.getElementById('price-base');
    if (priceElem) priceElem.innerText = "---";
  });

  connectLocalBridge();
});
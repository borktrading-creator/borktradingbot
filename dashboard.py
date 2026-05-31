"""
Dashboard web — Flask + HTML/JS en tiempo real
"""
import json
import os
import threading
import time
from flask import Flask, jsonify, render_template_string
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
PORT = int(os.getenv("PORT", 5000))

# Cache de datos
_cache = {"data": None, "analysis": None, "updated": 0}
_lock = threading.Lock()


def refresh_cache():
    """Actualiza el cache cada 5 minutos"""
    while True:
        try:
            from market_data import get_full_market_data
            from analyzer import run_full_analysis
            data = get_full_market_data()
            analysis = run_full_analysis(data)
            with _lock:
                _cache["data"] = data
                _cache["analysis"] = analysis
                _cache["updated"] = time.time()
        except Exception as e:
            print(f"Error actualizando cache: {e}")
        time.sleep(300)


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trading Bot — BTC/USDT</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Syne:wght@400;700;800&display=swap');
  :root {
    --bg: #080b10; --surface: #0d1117; --border: #1a2030;
    --accent: #00e5ff; --green: #00ff9d; --red: #ff3b6b;
    --yellow: #ffd600; --text: #cdd6f4; --muted: #45506a;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'JetBrains Mono', monospace; min-height: 100vh; }
  body::before { content: ''; position: fixed; inset: 0; background: radial-gradient(ellipse 80% 50% at 50% -20%, #00e5ff08, transparent); pointer-events: none; }

  .header { padding: 20px 24px 16px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
  .header-left .label { font-size: 9px; letter-spacing: 4px; color: var(--muted); margin-bottom: 4px; }
  .header-left .title { font-family: 'Syne', sans-serif; font-size: 24px; font-weight: 800; color: var(--accent); }
  .price-block { text-align: right; }
  .price-block .price { font-size: 32px; font-weight: 700; }
  .price-block .change { font-size: 12px; margin-top: 2px; }
  .price-up { color: var(--green); } .price-down { color: var(--red); }

  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; padding: 16px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 14px; transition: border-color 0.3s; }
  .card:hover { border-color: var(--accent); }
  .card-label { font-size: 9px; letter-spacing: 3px; color: var(--muted); margin-bottom: 10px; }

  .signal-row { display: flex; justify-content: space-between; align-items: flex-start; padding: 6px 0; border-bottom: 1px solid var(--border); }
  .signal-row:last-child { border-bottom: none; }
  .signal-name { font-size: 11px; font-weight: 600; color: var(--text); min-width: 80px; }
  .signal-msg { font-size: 10px; color: var(--muted); flex: 1; margin: 0 8px; }
  .signal-val { font-size: 10px; font-family: monospace; }
  .bull { color: var(--green); } .bear { color: var(--red); }
  .warn { color: var(--yellow); } .neutral { color: var(--muted); }

  .verdict-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin: 0 16px 12px; padding: 16px; display: flex; justify-content: space-between; align-items: center; }
  .verdict-text { font-family: 'Syne', sans-serif; font-size: 18px; font-weight: 800; }
  .score-bar { display: flex; gap: 8px; align-items: center; }
  .score-green { color: var(--green); font-size: 13px; }
  .score-red { color: var(--red); font-size: 13px; }

  .gauge-wrap { display: flex; flex-direction: column; align-items: center; }
  .gauge-val { font-size: 28px; font-weight: 700; margin-top: 4px; }
  .gauge-label { font-size: 9px; letter-spacing: 2px; margin-top: 2px; }

  .macro-event { padding: 8px 0; border-bottom: 1px solid var(--border); }
  .macro-event:last-child { border: none; }
  .macro-title { font-size: 11px; font-weight: 600; margin-bottom: 3px; }
  .macro-details { font-size: 10px; color: var(--muted); }

  .alerts-list { max-height: 180px; overflow-y: auto; }
  .alert-item { padding: 6px 8px; margin-bottom: 4px; border-radius: 4px; font-size: 11px; animation: fadeIn 0.4s ease; }
  .alert-bull { background: #00ff9d12; border-left: 2px solid var(--green); }
  .alert-bear { background: #ff3b6b12; border-left: 2px solid var(--red); }
  .alert-warn { background: #ffd60012; border-left: 2px solid var(--yellow); }

  .ls-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
  .ls-bar { height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; margin: 4px 0 8px; }
  .ls-fill { height: 100%; background: linear-gradient(90deg, var(--green), var(--red)); transition: width 0.5s; }

  .ts { font-size: 9px; color: var(--muted); text-align: center; padding: 12px; letter-spacing: 1px; }
  .dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--green); animation: blink 1.5s infinite; margin-right: 6px; }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
  @keyframes fadeIn { from{opacity:0;transform:translateX(-6px)} to{opacity:1;transform:none} }
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <div class="label"><span class="dot"></span>EN VIVO · BINANCE FUTURES</div>
    <div class="title">BTC / USDT</div>
  </div>
  <div class="price-block">
    <div class="price price-up" id="price">—</div>
    <div class="change" id="verdict">Cargando...</div>
  </div>
</div>

<!-- Veredicto de confluencia -->
<div class="verdict-card">
  <div>
    <div style="font-size:9px;letter-spacing:3px;color:var(--muted);margin-bottom:4px">CONFLUENCIA TOTAL</div>
    <div class="verdict-text" id="verdict-text">—</div>
  </div>
  <div class="score-bar">
    <div class="score-green">🟢 <span id="bull-score">0</span> pts</div>
    <div style="color:var(--muted);margin:0 6px">vs</div>
    <div class="score-red">🔴 <span id="bear-score">0</span> pts</div>
  </div>
</div>

<div class="grid">

  <!-- Indicadores Técnicos -->
  <div class="card" style="grid-column: span 2;">
    <div class="card-label">INDICADORES TÉCNICOS — 4H</div>
    <div id="tech-signals"></div>
  </div>

  <!-- RSI Gauge -->
  <div class="card">
    <div class="card-label">RSI · 14</div>
    <div class="gauge-wrap">
      <svg width="150" height="85" viewBox="0 0 150 85">
        <path d="M15,75 A60,60 0 0,1 135,75" fill="none" stroke="#1a2030" stroke-width="10" stroke-linecap="round"/>
        <path d="M15,75 A60,60 0 0,1 135,75" fill="none" stroke="#00ff9d" stroke-width="4" stroke-dasharray="0 68 126 0" stroke-linecap="round" opacity="0.4"/>
        <path d="M15,75 A60,60 0 0,1 135,75" fill="none" stroke="#ff3b6b" stroke-width="4" stroke-dasharray="0 126 68 0" stroke-linecap="round" opacity="0.4"/>
        <line id="rsi-needle" x1="75" y1="75" x2="75" y2="22" stroke="#00e5ff" stroke-width="2.5" stroke-linecap="round"/>
        <circle cx="75" cy="75" r="5" fill="#00e5ff"/>
      </svg>
      <div class="gauge-val" id="rsi-val">—</div>
      <div class="gauge-label" id="rsi-zone">—</div>
    </div>
  </div>

  <!-- Fear & Greed -->
  <div class="card">
    <div class="card-label">FEAR & GREED INDEX</div>
    <div class="gauge-wrap">
      <svg width="150" height="85" viewBox="0 0 150 85">
        <path d="M15,75 A60,60 0 0,1 135,75" fill="none" stroke="#1a2030" stroke-width="10" stroke-linecap="round"/>
        <line id="fg-needle" x1="75" y1="75" x2="75" y2="22" stroke="#ffd600" stroke-width="2.5" stroke-linecap="round"/>
        <circle cx="75" cy="75" r="5" fill="#ffd600"/>
      </svg>
      <div class="gauge-val" id="fg-val">—</div>
      <div class="gauge-label" id="fg-label">—</div>
    </div>
  </div>

  <!-- Long/Short Ratio -->
  <div class="card">
    <div class="card-label">LONG / SHORT RATIO</div>
    <div id="ls-content">Cargando...</div>
  </div>

  <!-- Liquidaciones -->
  <div class="card">
    <div class="card-label">LIQUIDACIONES RECIENTES</div>
    <div id="liq-content">Cargando...</div>
  </div>

  <!-- On-Chain / Sentimiento -->
  <div class="card">
    <div class="card-label">ON-CHAIN & SENTIMIENTO</div>
    <div id="onchain-signals"></div>
  </div>

  <!-- Calendario Macro -->
  <div class="card">
    <div class="card-label">📅 CALENDARIO MACRO USD</div>
    <div id="macro-content">Cargando...</div>
  </div>

  <!-- Alertas en tiempo real -->
  <div class="card" style="grid-column: span 2;">
    <div class="card-label">ALERTAS EN TIEMPO REAL</div>
    <div class="alerts-list" id="alerts-list">
      <div style="font-size:11px;color:var(--muted);text-align:center;padding:20px">Monitoreando mercado...</div>
    </div>
  </div>

</div>

<div class="ts" id="ts">Actualizando...</div>

<script>
const dirColors = { "BULLISH": "bull", "BEARISH": "bear", "WARNING": "warn", "NEUTRAL": "neutral" };
const dirEmoji = { "BULLISH": "🟢", "BEARISH": "🔴", "WARNING": "🟡", "NEUTRAL": "⚪" };
let alertsHistory = [];

function needle(id, val, max=100) {
  const angle = (val / max) * 180 - 90;
  const rad = (angle - 90) * Math.PI / 180;
  const x2 = 75 + 53 * Math.cos(rad);
  const y2 = 75 + 53 * Math.sin(rad);
  const el = document.getElementById(id);
  if (el) { el.setAttribute('x2', x2); el.setAttribute('y2', y2); }
}

function renderSignals(containerId, signals, filter) {
  const el = document.getElementById(containerId);
  if (!el || !signals) return;
  const filtered = signals.filter(s => filter(s));
  if (!filtered.length) { el.innerHTML = '<div style="color:var(--muted);font-size:11px">Sin señales</div>'; return; }
  el.innerHTML = filtered.map(s => `
    <div class="signal-row">
      <span class="signal-name">${dirEmoji[s.direction.name] || '⚪'} ${s.name}</span>
      <span class="signal-msg">${s.message}</span>
      <span class="signal-val ${dirColors[s.direction.name] || 'neutral'}">${s.value}</span>
    </div>`).join('');
}

async function fetchData() {
  try {
    const res = await fetch('/api/analysis');
    const d = await res.json();
    if (!d.ok) return;

    const a = d.analysis;
    const signals = a.signals || [];

    // Precio
    document.getElementById('price').textContent = '$' + a.price.toLocaleString('en', {maximumFractionDigits: 0});
    const priceEl = document.getElementById('price');
    priceEl.className = 'price ' + (a.bull_score >= a.bear_score ? 'price-up' : 'price-down');

    // Veredicto
    document.getElementById('verdict-text').textContent = a.verdict;
    document.getElementById('bull-score').textContent = a.bull_score;
    document.getElementById('bear-score').textContent = a.bear_score;

    // RSI
    const rsiSig = signals.find(s => s.name === 'RSI');
    if (rsiSig) {
      const rsi = parseFloat(rsiSig.value);
      document.getElementById('rsi-val').textContent = rsi.toFixed(1);
      needle('rsi-needle', rsi);
      const zone = rsi >= 70 ? '🔴 SOBRECOMPRA' : rsi <= 30 ? '🟢 SOBREVENTA' : '⚪ NEUTRAL';
      document.getElementById('rsi-zone').textContent = zone;
      document.getElementById('rsi-zone').className = 'gauge-label ' + (rsi >= 70 ? 'bear' : rsi <= 30 ? 'bull' : 'neutral');
    }

    // Fear & Greed
    if (d.fear_greed) {
      document.getElementById('fg-val').textContent = d.fear_greed.value + '/100';
      document.getElementById('fg-label').textContent = d.fear_greed.label;
      needle('fg-needle', d.fear_greed.value);
    }

    // Señales técnicas
    const techNames = ['RSI','MACD','EMA 9/21','Stochastic','Volumen','DMA 111','DMA 200','VPVR/POC'];
    renderSignals('tech-signals', signals, s => techNames.some(n => s.name.startsWith(n)));
    renderSignals('onchain-signals', signals, s => s.name.startsWith('Fear') || s.name.startsWith('Liq'));

    // L/S Ratio
    const lsEl = document.getElementById('ls-content');
    if (d.long_short && Object.keys(d.long_short).length) {
      const labels = {'4h':'4 horas','1h':'1 hora','12h':'12 horas'};
      lsEl.innerHTML = Object.entries(d.long_short).map(([tf, data]) => `
        <div class="ls-row">
          <span style="font-size:10px">${labels[tf]||tf}</span>
          <span style="font-size:11px;font-weight:600;color:${data.ratio>1?'var(--green)':'var(--red)'}">${data.ratio.toFixed(2)}</span>
        </div>
        <div class="ls-bar"><div class="ls-fill" style="width:${data.long_pct}%"></div></div>
        <div style="display:flex;justify-content:space-between;font-size:9px;color:var(--muted);margin-bottom:10px">
          <span>L: ${data.long_pct.toFixed(1)}%</span><span>S: ${data.short_pct.toFixed(1)}%</span>
        </div>`).join('');
    }

    // Liquidaciones
    const liqEl = document.getElementById('liq-content');
    if (d.liquidations) {
      const l = d.liquidations;
      liqEl.innerHTML = `
        <div style="text-align:center;margin-bottom:12px">
          <div style="font-size:22px;font-weight:700;color:var(--yellow)">$${(l.total/1e6).toFixed(2)}M</div>
          <div style="font-size:9px;color:var(--muted);letter-spacing:2px">TOTAL LIQUIDADO</div>
        </div>
        <div style="display:flex;justify-content:space-around">
          <div style="text-align:center">
            <div style="color:var(--red);font-size:14px;font-weight:700">$${(l.longs_liquidated/1e6).toFixed(2)}M</div>
            <div style="font-size:9px;color:var(--muted)">LONGS</div>
          </div>
          <div style="text-align:center">
            <div style="color:var(--green);font-size:14px;font-weight:700">$${(l.shorts_liquidated/1e6).toFixed(2)}M</div>
            <div style="font-size:9px;color:var(--muted)">SHORTS</div>
          </div>
        </div>`;
    }

    // Macro
    const macroEl = document.getElementById('macro-content');
    if (a.macro && a.macro.length) {
      macroEl.innerHTML = a.macro.map(e => `
        <div class="macro-event">
          <div class="macro-title">${e.title}</div>
          <div class="macro-details">📆 ${e.date} &nbsp;|&nbsp; Est: ${e.forecast} &nbsp;|&nbsp; Ant: ${e.previous} ${e.actual ? '&nbsp;|&nbsp; ✅ ' + e.actual : '&nbsp;|&nbsp; ⏳ Pendiente'}</div>
        </div>`).join('');
    } else {
      macroEl.innerHTML = '<div style="font-size:11px;color:var(--muted)">No hay eventos de alto impacto esta semana.</div>';
    }

    // Alertas críticas
    const critical = a.critical || [];
    if (critical.length) {
      critical.forEach(s => {
        const key = s.name + s.direction.name;
        if (!alertsHistory.includes(key)) {
          alertsHistory.unshift({ signal: s, time: new Date().toLocaleTimeString('es',{hour:'2-digit',minute:'2-digit',second:'2-digit'}) });
          alertsHistory = alertsHistory.slice(0, 10);
        }
      });
      const el = document.getElementById('alerts-list');
      el.innerHTML = alertsHistory.map(a => `
        <div class="alert-item alert-${dirColors[a.signal.direction.name] || 'warn'}">
          ${dirEmoji[a.signal.direction.name]} <strong>${a.signal.name}</strong>: ${a.signal.message}
          <span style="float:right;color:var(--muted);font-size:9px">${a.time}</span>
        </div>`).join('');
    }

    document.getElementById('ts').innerHTML = `<span class="dot"></span>Actualizado: ${a.timestamp}`;

  } catch(e) {
    console.error('Error:', e);
  }
}

fetchData();
setInterval(fetchData, 30000); // cada 30 segundos
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/analysis")
def api_analysis():
    with _lock:
        if _cache["analysis"] is None:
            return jsonify({"ok": False, "error": "Datos no disponibles aún"})

        analysis = _cache["analysis"]
        data = _cache["data"]

        # Serializa signals para JSON
        serialized_signals = []
        for s in analysis["signals"]:
            serialized_signals.append({
                "name": s.name,
                "direction": {"name": s.direction.name, "value": s.direction.value},
                "message": s.message,
                "value": s.value,
                "priority": s.priority,
            })

        critical_ser = []
        for s in analysis["critical"]:
            critical_ser.append({
                "name": s.name,
                "direction": {"name": s.direction.name, "value": s.direction.value},
                "message": s.message,
                "value": s.value,
            })

        return jsonify({
            "ok": True,
            "analysis": {
                "signals": serialized_signals,
                "critical": critical_ser,
                "bull_score": analysis["bull_score"],
                "bear_score": analysis["bear_score"],
                "verdict": analysis["verdict"],
                "price": analysis["price"],
                "timestamp": analysis["timestamp"],
                "macro": analysis["macro"],
            },
            "fear_greed": data.get("fear_greed"),
            "long_short": data.get("long_short"),
            "liquidations": data.get("liquidations"),
        })


@app.route("/health")
def health():
    """Endpoint de health check — mantiene Render.com despierto"""
    return jsonify({"status": "ok", "updated": _cache["updated"]})


def start_dashboard():
    # Inicia el hilo de actualización de datos
    t = threading.Thread(target=refresh_cache, daemon=True)
    t.start()

    # Carga inicial
    try:
        from market_data import get_full_market_data
        from analyzer import run_full_analysis
        data = get_full_market_data()
        analysis = run_full_analysis(data)
        with _lock:
            _cache["data"] = data
            _cache["analysis"] = analysis
            _cache["updated"] = time.time()
    except Exception as e:
        print(f"Error en carga inicial: {e}")

    app.run(host="0.0.0.0", port=PORT, debug=False)


if __name__ == "__main__":
    start_dashboard()

"""
Analizador de señales - detecta cada indicador por separado
y calcula confluencias según la estrategia del usuario
"""
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class Direction(Enum):
    BULLISH = "🟢 ALCISTA"
    BEARISH = "🔴 BAJISTA"
    NEUTRAL = "⚪ NEUTRAL"
    WARNING = "🟡 ATENCIÓN"


@dataclass
class Signal:
    name: str
    direction: Direction
    message: str
    value: str
    priority: int = 1  # 1=info, 2=importante, 3=crítico


def analyze_rsi(rsi: float) -> Signal:
    if rsi >= 75:
        return Signal("RSI", Direction.BEARISH,
                       f"RSI en SOBRECOMPRA extrema — posible techo",
                       f"{rsi:.1f}", priority=3)
    elif rsi >= 70:
        return Signal("RSI", Direction.BEARISH,
                       f"RSI en sobrecompra — debilidad alcista",
                       f"{rsi:.1f}", priority=2)
    elif rsi <= 25:
        return Signal("RSI", Direction.BULLISH,
                       f"RSI en SOBREVENTA extrema — posible suelo",
                       f"{rsi:.1f}", priority=3)
    elif rsi <= 30:
        return Signal("RSI", Direction.BULLISH,
                       f"RSI en sobreventa — posible rebote",
                       f"{rsi:.1f}", priority=2)
    elif rsi > 55:
        return Signal("RSI", Direction.BULLISH,
                       f"RSI en zona alcista sin extremos",
                       f"{rsi:.1f}", priority=1)
    elif rsi < 45:
        return Signal("RSI", Direction.BEARISH,
                       f"RSI en zona bajista sin extremos",
                       f"{rsi:.1f}", priority=1)
    else:
        return Signal("RSI", Direction.NEUTRAL,
                       f"RSI en zona neutral",
                       f"{rsi:.1f}", priority=1)


def analyze_macd(macd: float, signal: float, hist: float, prev_hist: float) -> Signal:
    cross_up = prev_hist < 0 and hist > 0
    cross_down = prev_hist > 0 and hist < 0
    weakening_bull = hist > 0 and hist < prev_hist
    weakening_bear = hist < 0 and hist > prev_hist

    if cross_up:
        return Signal("MACD", Direction.BULLISH,
                       "Cruce alcista MACD ✨ — momentum positivo",
                       f"Hist: {hist:.1f}", priority=3)
    elif cross_down:
        return Signal("MACD", Direction.BEARISH,
                       "Cruce bajista MACD ⚠️ — momentum negativo",
                       f"Hist: {hist:.1f}", priority=3)
    elif weakening_bull:
        return Signal("MACD", Direction.WARNING,
                       "MACD positivo pero perdiendo fuerza — posible giro",
                       f"Hist: {hist:.1f}", priority=2)
    elif weakening_bear:
        return Signal("MACD", Direction.WARNING,
                       "MACD negativo pero recuperando — presión bajista disminuye",
                       f"Hist: {hist:.1f}", priority=2)
    elif hist > 0:
        return Signal("MACD", Direction.BULLISH,
                       "MACD positivo — tendencia alcista",
                       f"Hist: {hist:.1f}", priority=1)
    else:
        return Signal("MACD", Direction.BEARISH,
                       "MACD negativo — tendencia bajista",
                       f"Hist: {hist:.1f}", priority=1)


def analyze_dma(price: float, dma111: float, dma200: float) -> List[Signal]:
    signals = []

    # DMA 111
    dist111 = ((price - dma111) / dma111) * 100
    if abs(dist111) < 0.3:
        signals.append(Signal("DMA 111", Direction.WARNING,
                               f"Precio TOCANDO DMA 111 — zona de decisión/rebote",
                               f"${dma111:.0f}", priority=2))
    elif price > dma111:
        signals.append(Signal("DMA 111", Direction.BULLISH,
                               f"Precio por ENCIMA de DMA 111 (+{dist111:.1f}%)",
                               f"${dma111:.0f}", priority=1))
    else:
        signals.append(Signal("DMA 111", Direction.BEARISH,
                               f"Precio por DEBAJO de DMA 111 ({dist111:.1f}%)",
                               f"${dma111:.0f}", priority=1))

    # DMA 200
    dist200 = ((price - dma200) / dma200) * 100
    if abs(dist200) < 0.3:
        signals.append(Signal("DMA 200", Direction.WARNING,
                               f"Precio TOCANDO DMA 200 — soporte/resistencia clave",
                               f"${dma200:.0f}", priority=3))
    elif price > dma200:
        signals.append(Signal("DMA 200", Direction.BULLISH,
                               f"Precio por ENCIMA de DMA 200 — tendencia alcista general",
                               f"${dma200:.0f}", priority=1))
    else:
        signals.append(Signal("DMA 200", Direction.BEARISH,
                               f"Precio por DEBAJO de DMA 200 — tendencia bajista general",
                               f"${dma200:.0f}", priority=2))
    return signals


def analyze_ema_cross(ema9: float, ema21: float, ema9_prev: float, ema21_prev: float) -> Signal:
    delta = ema9 - ema21
    prev_delta = ema9_prev - ema21_prev
    cross_up = prev_delta < 0 and delta > 0
    cross_down = prev_delta > 0 and delta < 0

    if cross_up:
        return Signal("EMA 9/21", Direction.BULLISH,
                       "Cruce alcista EMA 9 sobre EMA 21 🚀",
                       f"Δ {delta:.0f}", priority=3)
    elif cross_down:
        return Signal("EMA 9/21", Direction.BEARISH,
                       "Cruce bajista EMA 9 bajo EMA 21 📉",
                       f"Δ {delta:.0f}", priority=3)
    elif delta > 0:
        return Signal("EMA 9/21", Direction.BULLISH,
                       f"EMA 9 por encima de EMA 21 — impulso alcista",
                       f"Δ +{delta:.0f}", priority=1)
    else:
        return Signal("EMA 9/21", Direction.BEARISH,
                       f"EMA 9 por debajo de EMA 21 — impulso bajista",
                       f"Δ {delta:.0f}", priority=1)


def analyze_stochastic(k: float, d: float) -> Signal:
    cross_up = k > d and k < 20
    cross_down = k < d and k > 80

    if cross_up:
        return Signal("Stochastic", Direction.BULLISH,
                       f"Stoch cruce alcista en sobreventa — señal de compra",
                       f"K:{k:.0f} D:{d:.0f}", priority=3)
    elif cross_down:
        return Signal("Stochastic", Direction.BEARISH,
                       f"Stoch cruce bajista en sobrecompra — señal de venta",
                       f"K:{k:.0f} D:{d:.0f}", priority=3)
    elif k <= 20:
        return Signal("Stochastic", Direction.BULLISH,
                       f"Stochastic en zona de sobreventa",
                       f"K:{k:.0f} D:{d:.0f}", priority=2)
    elif k >= 80:
        return Signal("Stochastic", Direction.BEARISH,
                       f"Stochastic en zona de sobrecompra",
                       f"K:{k:.0f} D:{d:.0f}", priority=2)
    else:
        return Signal("Stochastic", Direction.NEUTRAL,
                       f"Stochastic en zona media — sin señal clara",
                       f"K:{k:.0f} D:{d:.0f}", priority=1)


def analyze_volume(volume: float, volume_ma: float) -> Signal:
    ratio = volume / volume_ma if volume_ma > 0 else 1
    if ratio > 1.5:
        return Signal("Volumen", Direction.WARNING,
                       f"Volumen un {(ratio-1)*100:.0f}% por encima de la media — movimiento con fuerza",
                       f"{ratio:.1f}x", priority=2)
    elif ratio < 0.5:
        return Signal("Volumen", Direction.NEUTRAL,
                       f"Volumen un {(1-ratio)*100:.0f}% por debajo de la media — mercado inactivo",
                       f"{ratio:.1f}x", priority=1)
    else:
        return Signal("Volumen", Direction.NEUTRAL,
                       f"Volumen normal",
                       f"{ratio:.1f}x", priority=1)


def analyze_fear_greed(fg: dict) -> Signal:
    val = fg.get("value", 50)
    label = fg.get("label", "Neutral")
    if val <= 20:
        return Signal("Fear & Greed", Direction.BULLISH,
                       f"Miedo extremo ({label}) — históricamente zona de compra",
                       f"{val}/100", priority=3)
    elif val <= 35:
        return Signal("Fear & Greed", Direction.BULLISH,
                       f"Miedo ({label}) — sesgo contrarian alcista",
                       f"{val}/100", priority=2)
    elif val >= 80:
        return Signal("Fear & Greed", Direction.BEARISH,
                       f"Codicia extrema ({label}) — históricamente zona de venta",
                       f"{val}/100", priority=3)
    elif val >= 65:
        return Signal("Fear & Greed", Direction.BEARISH,
                       f"Codicia ({label}) — precaución",
                       f"{val}/100", priority=2)
    else:
        return Signal("Fear & Greed", Direction.NEUTRAL,
                       f"Sentimiento neutral",
                       f"{val}/100", priority=1)


def analyze_long_short(ls: dict) -> List[Signal]:
    signals = []
    labels = {"4h": "4 horas", "1h": "1 hora", "12h": "12 horas"}
    for tf, data in ls.items():
        ratio = data.get("ratio", 1)
        long_pct = data.get("long_pct", 50)
        tf_label = labels.get(tf, tf)
        if ratio > 1.8:
            signals.append(Signal(f"L/S {tf_label}", Direction.WARNING,
                                   f"Ratio L/S muy alto en {tf_label} — riesgo de liquidación de longs",
                                   f"{ratio:.2f}", priority=2))
        elif ratio > 1.3:
            signals.append(Signal(f"L/S {tf_label}", Direction.BULLISH,
                                   f"Mayoría de posiciones son long en {tf_label}",
                                   f"{ratio:.2f}", priority=1))
        elif ratio < 0.7:
            signals.append(Signal(f"L/S {tf_label}", Direction.BEARISH,
                                   f"Mayoría de posiciones son short en {tf_label}",
                                   f"{ratio:.2f}", priority=1))
        else:
            signals.append(Signal(f"L/S {tf_label}", Direction.NEUTRAL,
                                   f"Ratio L/S equilibrado en {tf_label}",
                                   f"{ratio:.2f}", priority=1))
    return signals


def analyze_liquidations(liq: dict, price: float) -> Signal:
    total = liq.get("total", 0)
    longs_liq = liq.get("longs_liquidated", 0)
    shorts_liq = liq.get("shorts_liquidated", 0)

    if total > 50_000_000:
        dominant = "longs" if longs_liq > shorts_liq else "shorts"
        direction = Direction.BEARISH if dominant == "longs" else Direction.BULLISH
        return Signal("Liquidaciones", direction,
                       f"Liquidaciones altas: ${total/1e6:.1f}M — predominan {dominant}",
                       f"${total/1e6:.1f}M", priority=3)
    elif total > 10_000_000:
        return Signal("Liquidaciones", Direction.WARNING,
                       f"Liquidaciones moderadas: ${total/1e6:.1f}M",
                       f"${total/1e6:.1f}M", priority=2)
    else:
        return Signal("Liquidaciones", Direction.NEUTRAL,
                       f"Liquidaciones bajas — mercado tranquilo",
                       f"${total/1e6:.1f}M", priority=1)


def analyze_poc(price: float, poc: float) -> Signal:
    dist = ((price - poc) / poc) * 100
    if abs(dist) < 0.5:
        return Signal("VPVR/POC", Direction.WARNING,
                       f"Precio SOBRE el POC — zona de alta liquidez, decisión clave",
                       f"${poc:.0f}", priority=2)
    elif price > poc:
        return Signal("VPVR/POC", Direction.BULLISH,
                       f"Precio por encima del POC (+{dist:.1f}%) — zona de control alcista",
                       f"${poc:.0f}", priority=1)
    else:
        return Signal("VPVR/POC", Direction.BEARISH,
                       f"Precio por debajo del POC ({dist:.1f}%) — debajo de zona de control",
                       f"${poc:.0f}", priority=1)


def get_confluence_score(signals: List[Signal]) -> tuple:
    """Calcula score de confluencia bullish vs bearish"""
    bull = sum(s.priority for s in signals if s.direction == Direction.BULLISH)
    bear = sum(s.priority for s in signals if s.direction == Direction.BEARISH)
    total = bull + bear
    if total == 0:
        return 0, 0, "NEUTRAL"
    if bull > bear * 1.5:
        verdict = "CONFLUENCIA ALCISTA"
    elif bear > bull * 1.5:
        verdict = "CONFLUENCIA BAJISTA"
    else:
        verdict = "MERCADO MIXTO"
    return bull, bear, verdict


def run_full_analysis(market_data: dict) -> dict:
    """Ejecuta el análisis completo y devuelve todas las señales"""
    i4h = market_data["indicators_4h"]
    i1d = market_data["indicators_1d"]
    fg = market_data.get("fear_greed", {})
    ls = market_data.get("long_short", {})
    liq = market_data.get("liquidations", {})

    signals = []

    # Indicadores técnicos (4h - principal)
    signals.append(analyze_rsi(i4h["rsi"]))
    signals.append(analyze_macd(i4h["macd"], i4h["macd_signal"],
                                 i4h["macd_hist"], i4h["macd_prev_hist"]))
    signals.extend(analyze_dma(i4h["price"], i4h["dma111"], i4h["dma200"]))
    signals.append(analyze_ema_cross(i4h["ema9"], i4h["ema21"],
                                      i4h["ema9_prev"], i4h["ema21_prev"]))
    signals.append(analyze_stochastic(i4h["stoch_k"], i4h["stoch_d"]))
    signals.append(analyze_volume(i4h["volume"], i4h["volume_ma"]))
    signals.append(analyze_poc(i4h["price"], i4h["poc"]))

    # On-chain y sentimiento
    signals.append(analyze_fear_greed(fg))
    signals.extend(analyze_long_short(ls))
    signals.append(analyze_liquidations(liq, i4h["price"]))

    # Score de confluencia
    bull_score, bear_score, verdict = get_confluence_score(signals)

    # Señales críticas (prioridad 3)
    critical = [s for s in signals if s.priority == 3]

    return {
        "signals": signals,
        "critical": critical,
        "bull_score": bull_score,
        "bear_score": bear_score,
        "verdict": verdict,
        "price": i4h["price"],
        "timestamp": i4h["timestamp"],
        "macro": market_data.get("macro", []),
    }

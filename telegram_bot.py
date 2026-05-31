"""
Bot de Telegram — alertas de trading
"""
import asyncio
import logging
import os
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv

from market_data import get_full_market_data
from analyzer import run_full_analysis, Direction

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Estado previo para detectar cambios
prev_signals = {}


def format_direction_emoji(direction: Direction) -> str:
    return direction.value.split()[0]


def format_signal_message(signal) -> str:
    emoji = format_direction_emoji(signal.direction)
    return f"{emoji} *{signal.name}*: {signal.message} `[{signal.value}]`"


def build_full_report(analysis: dict) -> str:
    """Construye el mensaje completo de estado del mercado"""
    price = analysis["price"]
    verdict = analysis["verdict"]
    bull = analysis["bull_score"]
    bear = analysis["bear_score"]
    ts = analysis["timestamp"]
    signals = analysis["signals"]

    # Emoji de veredicto
    if "ALCISTA" in verdict:
        v_emoji = "🟢"
    elif "BAJISTA" in verdict:
        v_emoji = "🔴"
    else:
        v_emoji = "⚪"

    lines = [
        f"📊 *ANÁLISIS BTC/USDT — 4H*",
        f"💰 Precio: `${price:,.0f}`",
        f"🕐 {ts}",
        f"",
        f"{v_emoji} *{verdict}*",
        f"Alcista: {bull} pts | Bajista: {bear} pts",
        f"",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"*INDICADORES TÉCNICOS*",
        f"━━━━━━━━━━━━━━━━━━━━",
    ]

    # Agrupa señales por categoría
    tech_names = ["RSI", "MACD", "EMA 9/21", "Stochastic", "Volumen", "DMA 111", "DMA 200", "VPVR/POC"]
    onchain_names = ["Fear & Greed", "Liquidaciones"]

    for s in signals:
        if any(s.name.startswith(n) for n in tech_names):
            lines.append(format_signal_message(s))

    lines += ["", "━━━━━━━━━━━━━━━━━━━━", "*ON-CHAIN & SENTIMIENTO*", "━━━━━━━━━━━━━━━━━━━━"]

    for s in signals:
        if any(s.name.startswith(n) for n in onchain_names):
            lines.append(format_signal_message(s))

    lines += ["", "━━━━━━━━━━━━━━━━━━━━", "*LONG/SHORT RATIO*", "━━━━━━━━━━━━━━━━━━━━"]

    for s in signals:
        if s.name.startswith("L/S"):
            lines.append(format_signal_message(s))

    # Macro
    macro = analysis.get("macro", [])
    if macro:
        lines += ["", "━━━━━━━━━━━━━━━━━━━━", "*📅 CALENDARIO MACRO (USD)*", "━━━━━━━━━━━━━━━━━━━━"]
        for e in macro[:4]:
            actual = f"✅ Real: {e['actual']}" if e.get("actual") else "⏳ Pendiente"
            lines.append(
                f"📌 *{e['title']}*\n"
                f"   📆 {e['date']} | Prev: {e['previous']} | Est: {e['forecast']} | {actual}"
            )

    lines.append(f"\n_Actualizado: {ts}_")
    return "\n".join(lines)


def build_critical_alert(signal) -> str:
    """Mensaje corto para alertas críticas"""
    emoji = format_direction_emoji(signal.direction)
    return (
        f"🚨 *ALERTA CRÍTICA*\n\n"
        f"{emoji} *{signal.name}*\n"
        f"{signal.message}\n"
        f"Valor: `{signal.value}`\n\n"
        f"_BTC/USDT 4H — {datetime.now().strftime('%H:%M UTC')}_"
    )


def build_confluence_alert(analysis: dict) -> str:
    """Alerta especial cuando hay múltiples confluencias"""
    verdict = analysis["verdict"]
    bull = analysis["bull_score"]
    bear = analysis["bear_score"]
    price = analysis["price"]
    critical = analysis["critical"]

    if "ALCISTA" in verdict:
        header = "🟢🟢🟢 *CONFLUENCIA ALCISTA DETECTADA* 🟢🟢🟢"
    else:
        header = "🔴🔴🔴 *CONFLUENCIA BAJISTA DETECTADA* 🔴🔴🔴"

    lines = [
        header,
        f"",
        f"💰 BTC: `${price:,.0f}`",
        f"Score → Alcista: {bull} | Bajista: {bear}",
        f"",
        f"*Señales críticas activas:*",
    ]
    for s in critical:
        lines.append(f"  {format_direction_emoji(s.direction)} {s.name}: {s.message}")

    lines.append(f"\n_⚠️ Esto no es consejo financiero — verifica siempre_")
    return "\n".join(lines)


async def send_message(bot: Bot, text: str, chat_id: str = None):
    """Envía mensaje con manejo de errores"""
    target = chat_id or CHAT_ID
    if not target:
        logger.warning("No hay CHAT_ID configurado")
        return
    try:
        await bot.send_message(
            chat_id=target,
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Error enviando mensaje: {e}")


# ─── COMANDOS DEL BOT ────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"👋 *Bot de Trading BTC/USDT activo*\n\n"
        f"Tu Chat ID es: `{chat_id}`\n"
        f"Cópialo en tu archivo `.env` como `TELEGRAM_CHAT_ID={chat_id}`\n\n"
        f"*Comandos disponibles:*\n"
        f"/estado — Análisis completo ahora\n"
        f"/rsi — Solo RSI actual\n"
        f"/macd — Solo MACD actual\n"
        f"/macro — Calendario económico\n"
        f"/liquidaciones — Datos de liquidaciones\n"
        f"/fear — Fear & Greed Index\n"
        f"/ls — Long/Short ratio\n"
        f"/ayuda — Ver todos los comandos",
        parse_mode=ParseMode.MARKDOWN
    )


async def cmd_estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Obteniendo datos del mercado...")
    try:
        data = get_full_market_data()
        analysis = run_full_analysis(data)
        msg = build_full_report(analysis)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_rsi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from market_data import get_candles, get_indicators
        df = get_candles(interval="4h", limit=50)
        ind = get_indicators(df)
        rsi = ind["rsi"]
        if rsi >= 70:
            zona = "🔴 SOBRECOMPRA"
        elif rsi <= 30:
            zona = "🟢 SOBREVENTA"
        else:
            zona = "⚪ NEUTRAL"
        await update.message.reply_text(
            f"📈 *RSI BTC/USDT 4H*\n\nValor: `{rsi:.1f}`\nZona: {zona}",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_macd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from market_data import get_candles, get_indicators
        df = get_candles(interval="4h", limit=100)
        ind = get_indicators(df)
        hist = ind["macd_hist"]
        prev = ind["macd_prev_hist"]
        trend = "📈 Subiendo" if hist > prev else "📉 Bajando"
        zone = "🟢 Positivo" if hist > 0 else "🔴 Negativo"
        await update.message.reply_text(
            f"📊 *MACD BTC/USDT 4H*\n\n"
            f"Histograma: `{hist:.1f}`\n"
            f"Zona: {zone}\n"
            f"Momentum: {trend}",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_macro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from market_data import get_macro_calendar
        events = get_macro_calendar()
        if not events:
            await update.message.reply_text("📅 No hay eventos macro de alto impacto esta semana.")
            return
        lines = ["📅 *CALENDARIO MACRO USD — Esta semana*\n"]
        for e in events:
            actual = f"✅ {e['actual']}" if e.get("actual") else "⏳ Pendiente"
            lines.append(
                f"📌 *{e['title']}*\n"
                f"   {e['date']}\n"
                f"   Anterior: {e['previous']} | Est: {e['forecast']} | {actual}\n"
            )
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_liquidaciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from market_data import get_liquidations
        liq = get_liquidations()
        total = liq["total"]
        longs = liq["longs_liquidated"]
        shorts = liq["shorts_liquidated"]
        await update.message.reply_text(
            f"💥 *LIQUIDACIONES BTC (última hora)*\n\n"
            f"Total: `${total/1e6:.2f}M`\n"
            f"🔴 Longs liquidados: `${longs/1e6:.2f}M`\n"
            f"🟢 Shorts liquidados: `${shorts/1e6:.2f}M`",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_fear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from market_data import get_fear_greed
        fg = get_fear_greed()
        val = fg["value"]
        label = fg["label"]
        if val <= 25:
            emoji = "😱"
        elif val <= 40:
            emoji = "😨"
        elif val <= 60:
            emoji = "😐"
        elif val <= 75:
            emoji = "😏"
        else:
            emoji = "🤑"
        await update.message.reply_text(
            f"😱 *FEAR & GREED INDEX*\n\n{emoji} `{val}/100` — {label}",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_ls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        from market_data import get_long_short_ratio
        ls = get_long_short_ratio()
        lines = ["⚖️ *LONG/SHORT RATIO BTC*\n"]
        labels = {"4h": "4 horas", "1h": "1 hora", "12h": "12 horas"}
        for tf, data in ls.items():
            emoji = "🟢" if data["ratio"] > 1 else "🔴"
            lines.append(
                f"{emoji} *{labels.get(tf, tf)}*: `{data['ratio']:.2f}` "
                f"(L: {data['long_pct']:.1f}% / S: {data['short_pct']:.1f}%)"
            )
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Comandos del Bot*\n\n"
        "/estado — Análisis completo del mercado\n"
        "/rsi — RSI actual 4H\n"
        "/macd — MACD actual 4H\n"
        "/macro — Calendario económico\n"
        "/liquidaciones — Liquidaciones recientes\n"
        "/fear — Fear & Greed Index\n"
        "/ls — Long/Short ratio\n"
        "/ayuda — Este mensaje\n\n"
        "📢 Las alertas automáticas se envían cada 4h y cuando hay señales críticas.",
        parse_mode=ParseMode.MARKDOWN
    )


# ─── SCHEDULER: ALERTAS AUTOMÁTICAS ─────────────────────────────────

async def scheduled_check(bot: Bot):
    """Se ejecuta cada 4h — analiza y alerta si hay señales críticas"""
    global prev_signals
    logger.info("Ejecutando chequeo programado...")

    try:
        data = get_full_market_data()
        analysis = run_full_analysis(data)

        # Alerta de confluencia si score alto
        bull = analysis["bull_score"]
        bear = analysis["bear_score"]
        if bull >= 8 or bear >= 8:
            await send_message(bot, build_confluence_alert(analysis))
        elif analysis["critical"]:
            # Alertas individuales críticas
            for signal in analysis["critical"]:
                key = f"{signal.name}_{signal.direction.name}"
                if prev_signals.get(key) != signal.value:
                    prev_signals[key] = signal.value
                    await send_message(bot, build_critical_alert(signal))
                    await asyncio.sleep(1)

        # Reporte diario a las 8h UTC (primera ejecución del día)
        hour = datetime.utcnow().hour
        if hour == 8:
            await send_message(bot, build_full_report(analysis))

    except Exception as e:
        logger.error(f"Error en chequeo programado: {e}")


def run_bot():
    """Arranca el bot de Telegram"""
    app = Application.builder().token(TOKEN).build()

    # Registra comandos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("estado", cmd_estado))
    app.add_handler(CommandHandler("rsi", cmd_rsi))
    app.add_handler(CommandHandler("macd", cmd_macd))
    app.add_handler(CommandHandler("macro", cmd_macro))
    app.add_handler(CommandHandler("liquidaciones", cmd_liquidaciones))
    app.add_handler(CommandHandler("fear", cmd_fear))
    app.add_handler(CommandHandler("ls", cmd_ls))
    app.add_handler(CommandHandler("ayuda", cmd_ayuda))

    # Job de chequeo cada 4 horas
    app.job_queue.run_repeating(
        lambda ctx: asyncio.create_task(scheduled_check(ctx.bot)),
        interval=14400,  # 4 horas en segundos
        first=60
    )

    logger.info("Bot iniciado ✅")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run_bot()

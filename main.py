"""
Punto de entrada principal — arranca el bot de Telegram y el dashboard web
"""
import threading
import logging
import os
import sys
import time

# Añade src al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def run_dashboard():
    """Arranca el dashboard Flask en un hilo separado"""
    from src.dashboard import start_dashboard
    logger.info("Iniciando dashboard web...")
    start_dashboard()


def run_telegram_bot():
    """Arranca el bot de Telegram"""
    from src.telegram_bot import run_bot
    logger.info("Iniciando bot de Telegram...")
    run_bot()


def keep_alive():
    """Hace ping al propio servidor cada 10 min para que Render no se duerma"""
    import requests
    port = os.getenv("PORT", "5000")
    url = f"http://localhost:{port}/health"
    time.sleep(30)  # Espera inicial
    while True:
        try:
            requests.get(url, timeout=5)
            logger.debug("Keep-alive ping OK")
        except Exception:
            pass
        time.sleep(600)  # 10 minutos


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("  TRADING BOT BTC/USDT — INICIANDO")
    logger.info("=" * 50)

    # Verifica configuración básica
    token = os.getenv("TELEGRAM_TOKEN")
    if not token or token == "TU_TOKEN_AQUI":
        logger.error("❌ TELEGRAM_TOKEN no configurado en .env")
        sys.exit(1)

    # Hilo del dashboard web
    t_dashboard = threading.Thread(target=run_dashboard, daemon=True)
    t_dashboard.start()
    time.sleep(3)  # Espera a que arranque Flask

    # Hilo de keep-alive (para Render.com)
    t_alive = threading.Thread(target=keep_alive, daemon=True)
    t_alive.start()

    # Bot de Telegram en el hilo principal
    run_telegram_bot()

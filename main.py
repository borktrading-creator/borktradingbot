import threading, logging, os, sys, time
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_dashboard():
    from dashboard import start_dashboard
    start_dashboard()

def run_telegram_bot():
    from telegram_bot import run_bot
    run_bot()

def keep_alive():
    import requests
    port = os.getenv("PORT", "5000")
    time.sleep(30)
    while True:
        try: requests.get(f"http://localhost:{port}/health", timeout=5)
        except: pass
        time.sleep(600)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_dashboard, daemon=True)
    t1.start()
    time.sleep(3)
    threading.Thread(target=keep_alive, daemon=True).start()
    run_telegram_bot()

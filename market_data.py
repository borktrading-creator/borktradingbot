"""
Módulo de datos de mercado - Binance + APIs externas
"""
import requests
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime
from binance.client import Client
import os
from dotenv import load_dotenv

load_dotenv()

client = Client(os.getenv("BINANCE_API_KEY"), os.getenv("BINANCE_API_SECRET"))
SYMBOL = os.getenv("SYMBOL", "BTCUSDT")


def get_candles(symbol=SYMBOL, interval="4h", limit=200):
    """Obtiene velas de Binance y calcula indicadores"""
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        "time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    df.set_index("time", inplace=True)
    return df


def get_indicators(df):
    """Calcula todos los indicadores técnicos"""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # RSI
    rsi = ta.rsi(close, length=14)
    rsi_val = float(rsi.iloc[-1]) if rsi is not None else 50.0

    # MACD
    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    macd_val = float(macd_df["MACD_12_26_9"].iloc[-1]) if macd_df is not None else 0.0
    macd_signal = float(macd_df["MACDs_12_26_9"].iloc[-1]) if macd_df is not None else 0.0
    macd_hist = float(macd_df["MACDh_12_26_9"].iloc[-1]) if macd_df is not None else 0.0
    macd_prev_hist = float(macd_df["MACDh_12_26_9"].iloc[-2]) if macd_df is not None else 0.0

    # DMAs
    dma111 = float(ta.sma(close, length=111).iloc[-1])
    dma200 = float(ta.sma(close, length=200).iloc[-1])

    # EMA cruce (delta)
    ema9 = float(ta.ema(close, length=9).iloc[-1])
    ema21 = float(ta.ema(close, length=21).iloc[-1])
    ema9_prev = float(ta.ema(close, length=9).iloc[-2])
    ema21_prev = float(ta.ema(close, length=21).iloc[-2])

    # Stochastic
    stoch = ta.stoch(high, low, close, k=14, d=3, smooth_k=3)
    stoch_k = float(stoch["STOCHk_14_3_3"].iloc[-1]) if stoch is not None else 50.0
    stoch_d = float(stoch["STOCHd_14_3_3"].iloc[-1]) if stoch is not None else 50.0

    # VPVR simplificado - POC (precio con más volumen)
    price_bins = pd.cut(df["close"], bins=20)
    vol_by_price = df.groupby(price_bins, observed=True)["volume"].sum()
    poc_interval = vol_by_price.idxmax()
    poc_price = float(poc_interval.mid) if poc_interval is not None else float(close.iloc[-1])

    # Bollinger Bands
    bb = ta.bbands(close, length=20, std=2)
    bb_upper = float(bb["BBU_20_2.0"].iloc[-1]) if bb is not None else 0.0
    bb_lower = float(bb["BBL_20_2.0"].iloc[-1]) if bb is not None else 0.0
    bb_mid = float(bb["BBM_20_2.0"].iloc[-1]) if bb is not None else 0.0

    current_price = float(close.iloc[-1])

    return {
        "price": current_price,
        "rsi": rsi_val,
        "macd": macd_val,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist,
        "macd_prev_hist": macd_prev_hist,
        "dma111": dma111,
        "dma200": dma200,
        "ema9": ema9,
        "ema21": ema21,
        "ema9_prev": ema9_prev,
        "ema21_prev": ema21_prev,
        "stoch_k": stoch_k,
        "stoch_d": stoch_d,
        "poc": poc_price,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "bb_mid": bb_mid,
        "volume": float(volume.iloc[-1]),
        "volume_ma": float(ta.sma(volume, length=20).iloc[-1]),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
    }


def get_fear_greed():
    """Fear & Greed Index de Alternative.me"""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        data = r.json()["data"][0]
        return {
            "value": int(data["value"]),
            "label": data["value_classification"],
        }
    except Exception:
        return {"value": 50, "label": "Neutral"}


def get_long_short_ratio(symbol="BTCUSDT"):
    """Long/Short ratio de Binance Futures"""
    try:
        ratios = {}
        for period in ["4h", "1h", "12h"]:
            url = f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
            r = requests.get(url, params={"symbol": symbol, "period": period, "limit": 1}, timeout=10)
            data = r.json()
            if data:
                ratios[period] = {
                    "long_pct": float(data[0]["longAccount"]) * 100,
                    "short_pct": float(data[0]["shortAccount"]) * 100,
                    "ratio": float(data[0]["longShortRatio"]),
                }
        return ratios
    except Exception:
        return {}


def get_liquidations(symbol="BTCUSDT"):
    """Datos de liquidaciones recientes de Binance Futures"""
    try:
        url = "https://fapi.binance.com/fapi/v1/allForceOrders"
        r = requests.get(url, params={"symbol": symbol, "limit": 50}, timeout=10)
        data = r.json()
        longs = sum(float(x["origQty"]) * float(x["price"]) for x in data if x["side"] == "SELL")
        shorts = sum(float(x["origQty"]) * float(x["price"]) for x in data if x["side"] == "BUY")
        return {
            "longs_liquidated": longs,
            "shorts_liquidated": shorts,
            "total": longs + shorts,
            "raw": data[:10],
        }
    except Exception:
        return {"longs_liquidated": 0, "shorts_liquidated": 0, "total": 0, "raw": []}


def get_open_interest(symbol="BTCUSDT"):
    """Open Interest de Binance Futures"""
    try:
        url = "https://fapi.binance.com/fapi/v1/openInterest"
        r = requests.get(url, params={"symbol": symbol}, timeout=10)
        data = r.json()
        return float(data["openInterest"])
    except Exception:
        return 0.0


def get_macro_calendar():
    """Eventos macro próximos via ForexFactory (scraping básico)"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json",
                         headers=headers, timeout=10)
        events = r.json()
        important = [
            e for e in events
            if e.get("impact") == "High" and e.get("country") in ["USD", "US"]
        ]
        result = []
        for e in important[:5]:
            result.append({
                "title": e.get("title", ""),
                "date": e.get("date", ""),
                "forecast": e.get("forecast", "N/A"),
                "previous": e.get("previous", "N/A"),
                "actual": e.get("actual", ""),
            })
        return result
    except Exception:
        return []


def get_full_market_data():
    """Obtiene todos los datos del mercado de una vez"""
    df_4h = get_candles(interval="4h", limit=200)
    df_1d = get_candles(interval="1d", limit=200)

    indicators_4h = get_indicators(df_4h)
    indicators_1d = get_indicators(df_1d)

    return {
        "indicators_4h": indicators_4h,
        "indicators_1d": indicators_1d,
        "fear_greed": get_fear_greed(),
        "long_short": get_long_short_ratio(),
        "liquidations": get_liquidations(),
        "open_interest": get_open_interest(),
        "macro": get_macro_calendar(),
        "candles_4h": df_4h.tail(50).reset_index().to_dict("records"),
    }

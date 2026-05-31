# 🤖 GUÍA DE INSTALACIÓN — Trading Bot BTC/USDT

## LO QUE NECESITAS ANTES DE EMPEZAR
- Cuenta en GitHub (gratis): https://github.com
- Cuenta en Render.com (gratis): https://render.com
- API de Binance (solo lectura, gratis)

---

## PASO 1 — Obtén tu Chat ID de Telegram

1. Abre Telegram y busca tu bot (el que creaste con @BotFather)
2. Escríbele `/start`
3. El bot te responderá con tu **Chat ID** (un número)
4. Cópialo — lo necesitarás en el Paso 3

---

## PASO 2 — Crea tu API de Binance (solo lectura)

1. Entra en binance.com > Perfil (arriba derecha) > **API Management**
2. Haz clic en **Create API**
3. Tipo: **System generated**
4. Ponle un nombre: `trading-bot`
5. ⚠️ **MUY IMPORTANTE**: Activa SOLO "Enable Reading" — NO actives trading ni retiros
6. Completa la verificación
7. Copia la **API Key** y el **Secret Key**

---

## PASO 3 — Sube el código a GitHub

1. Ve a https://github.com/new
2. Nombre del repositorio: `trading-bot-btc`
3. Ponlo en **Privado** ✅
4. Haz clic en **Create repository**
5. En la página siguiente, haz clic en **uploading an existing file**
6. Sube todos los archivos del ZIP que te he dado
7. Haz clic en **Commit changes**

---

## PASO 4 — Configura las variables de entorno

Antes de deployar, edita el archivo `.env` con tus datos:

```
TELEGRAM_TOKEN=8897431357:AAHa2SeK_lI34vhVLZB8eHq0r1Hm6TLTJRw
TELEGRAM_CHAT_ID=<el número que te dio el bot en el Paso 1>
BINANCE_API_KEY=<tu API key de Binance>
BINANCE_API_SECRET=<tu Secret key de Binance>
```

⚠️ El archivo `.env` NO se sube a GitHub — ya está en el .gitignore

---

## PASO 5 — Despliega en Render.com

1. Ve a https://render.com y crea una cuenta con tu GitHub
2. Haz clic en **New +** > **Web Service**
3. Conecta tu repositorio `trading-bot-btc`
4. Configuración:
   - **Name**: trading-bot-btc
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
5. Haz clic en **Advanced** > **Add Environment Variable** y añade:
   - `TELEGRAM_TOKEN` = tu token
   - `TELEGRAM_CHAT_ID` = tu chat id
   - `BINANCE_API_KEY` = tu api key
   - `BINANCE_API_SECRET` = tu secret key
   - `SYMBOL` = BTCUSDT
   - `TIMEFRAME` = 4h
6. Haz clic en **Create Web Service**
7. Espera 2-3 minutos mientras se instala

---

## PASO 6 — Verifica que funciona

1. En Render, verás una URL tipo: `https://trading-bot-btc.onrender.com`
2. Abre esa URL en el navegador → verás el **dashboard**
3. En Telegram, escríbele `/start` a tu bot → debe responder
4. Escríbele `/estado` → recibirás el análisis completo

---

## COMANDOS DEL BOT

| Comando | Qué hace |
|---------|----------|
| `/start` | Inicia el bot y muestra tu Chat ID |
| `/estado` | Análisis completo del mercado ahora |
| `/rsi` | Solo el RSI actual |
| `/macd` | Solo el MACD actual |
| `/macro` | Calendario económico esta semana |
| `/liquidaciones` | Liquidaciones recientes |
| `/fear` | Fear & Greed Index |
| `/ls` | Long/Short ratio |
| `/ayuda` | Lista de comandos |

---

## ALERTAS AUTOMÁTICAS

El bot te enviará alertas automáticas cuando:
- 🚨 RSI toque sobrecompra/sobreventa extrema
- 🚨 Cruce de MACD
- 🚨 Cruce de EMAs
- 🚨 Stochastic en zonas extremas con cruce
- 🟢🟢🟢 Cuando hay CONFLUENCIA ALCISTA fuerte
- 🔴🔴🔴 Cuando hay CONFLUENCIA BAJISTA fuerte
- 📅 Reporte diario completo a las 8:00 UTC

---

## PROBLEMAS FRECUENTES

**El bot no responde:**
- Verifica que el TELEGRAM_TOKEN esté bien copiado en Render
- Mira los logs en Render > tu servicio > Logs

**Error de Binance:**
- Verifica que la API key tenga permiso de lectura
- Si usas IP restriction en Binance, desactívala o añade la IP de Render

**Render se duerme:**
- El keep-alive automático lo evita, pero el plan free tiene límites
- Si se duerme, simplemente abre el dashboard y se despertará

---

## ESTRUCTURA DEL PROYECTO

```
tradingbot/
├── main.py              ← Punto de entrada principal
├── requirements.txt     ← Dependencias Python
├── render.yaml          ← Config de Render.com
├── .env                 ← Tus credenciales (NO subir a GitHub)
├── .env.example         ← Plantilla del .env
└── src/
    ├── market_data.py   ← Datos de Binance + APIs externas
    ├── analyzer.py      ← Lógica de señales e indicadores
    ├── telegram_bot.py  ← Bot de Telegram + comandos
    └── dashboard.py     ← Dashboard web en tiempo real
```

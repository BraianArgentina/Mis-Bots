import time
import pandas as pd
import requests
from binance.client import Client
import config  # <--- IMPORTAMOS TU CAJA FUERTE (config.py)

# --- CONEXIÓN SEGURA ---
# Toma las claves y el modo (Testnet False/True) desde tu archivo config.py
client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=config.TESTNET_MODE)

# --- 🚑 LISTA DE PACIENTES (Tus monedas atrapadas) ---
WATCHLIST = ['DEGENUSDT', 'TRXUSDT', 'WIFUSDT', 'DEXEUSDT', 'ATHUSDT']

# --- ❄️ CONFIGURACIÓN DE SILENCIO (COOLDOWN) ---
# Tiempo en segundos que la moneda se callará tras una alerta
# 4 Horas = 14400 segundos
COOLDOWN_SECONDS = 14400

# Diccionario para recordar cuándo fue el último aviso de cada moneda
last_alert_times = {}

# --- TELEGRAM ---
def send_telegram_alert(message):
    try:
        # Usa el Token y ID desde config.py
        url = f'https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage'
        payload = {'chat_id': config.TELEGRAM_CHAT_ID, 'text': message}
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}")

# --- INDICADORES MATEMÁTICOS ---

def bcwsma(series, length, weight):
    result = []
    for i in range(len(series)):
        if i == 0:
            result.append(series[i])
        else:
            prev = result[-1]
            value = (weight * series[i] + (length - weight) * prev) / length
            result.append(value)
    return pd.Series(result)

def calculate_kdj(df, ilong=9, isig=3):
    low_list = df['low'].rolling(window=ilong).min()
    high_list = df['high'].rolling(window=ilong).max()
    rsv = 100 * ((df['close'] - low_list) / (high_list - low_list))
    k = bcwsma(rsv.fillna(50), isig, 1)
    d = bcwsma(k.fillna(50), isig, 1)
    j = 3 * k - 2 * d
    return k, d, j

def calculate_bollinger_bands(df, period=20, std_dev=2):
    sma = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    return upper, lower

def get_klines_safe(symbol, interval):
    try:
        # Pedimos 100 velas para asegurar cálculos de 4H
        klines = client.futures_klines(symbol=symbol, interval=interval, limit=100)
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'q', 'n', 'v', 'q2', 'i'])
        df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
        return df
    except:
        return pd.DataFrame()

# --- LÓGICA DE RESCATE ---
def run_rescue_bot():
    print("🚑 Iniciando Protocolo de Rescate V2 en PythonAnywhere...")
    send_telegram_alert(f"🚑 Bot Defensor ONLINE. Vigilando: {len(WATCHLIST)} pacientes.")
    print(f"👀 Vigilando: {WATCHLIST}")
    print(f"❄️ Modo Silencio: {COOLDOWN_SECONDS/3600} horas tras alerta.")

    while True:
        current_time = time.time()

        for symbol in WATCHLIST:
            try:
                # 1. Chequeo de Cooldown (¿Está la moneda castigada?)
                if symbol in last_alert_times:
                    tiempo_pasado = current_time - last_alert_times[symbol]
                    if tiempo_pasado < COOLDOWN_SECONDS:
                        continue

                # 2. Descargar datos
                df_15m = get_klines_safe(symbol, '15m')
                df_1h = get_klines_safe(symbol, '1h')
                df_4h = get_klines_safe(symbol, '4h')

                if df_4h.empty: continue

                # 3. Indicadores
                _, _, j15 = calculate_kdj(df_15m)
                _, _, j1h = calculate_kdj(df_1h)
                _, _, j4h = calculate_kdj(df_4h)

                up_1h, low_1h = calculate_bollinger_bands(df_1h)
                up_4h, low_4h = calculate_bollinger_bands(df_4h)

                j15_v = j15.iloc[-1]
                j1h_v = j1h.iloc[-1]
                j4h_v = j4h.iloc[-1]
                close = df_15m['close'].iloc[-1]

                techo_4h = up_4h.iloc[-1]
                piso_4h = low_4h.iloc[-1]

                alerta_enviada = False

                # --- CONDICIÓN LONG (SUELO) ---
                if j4h_v < 20 and j1h_v < 10 and j15_v < 5:
                    msg = (f"🚑 OPORTUNIDAD DCA LONG (Suelo) en {symbol}\n"
                           f"Precio: {close}\n"
                           f"Soporte 4H: {piso_4h:.4f}\n"
                           f"----------------\n"
                           f"J(15m): {j15_v:.1f}\n"
                           f"J(1H):  {j1h_v:.1f}\n"
                           f"J(4H):  {j4h_v:.1f}\n"
                           f"⏱️ Alerta pausada por 4 horas.")
                    send_telegram_alert(msg)
                    print(f"✅ Alerta LONG enviada para {symbol}. Iniciando cooldown.")
                    alerta_enviada = True

                # --- CONDICIÓN SHORT (TECHO) ---
                elif j4h_v > 80 and j1h_v > 90 and j15_v > 100:
                    msg = (f"🚑 OPORTUNIDAD DCA SHORT (Techo) en {symbol}\n"
                           f"Precio: {close}\n"
                           f"Resistencia 4H: {techo_4h:.4f}\n"
                           f"----------------\n"
                           f"J(15m): {j15_v:.1f}\n"
                           f"J(1H):  {j1h_v:.1f}\n"
                           f"J(4H):  {j4h_v:.1f}\n"
                           f"⏱️ Alerta pausada por 4 horas.")
                    send_telegram_alert(msg)
                    print(f"✅ Alerta SHORT enviada para {symbol}. Iniciando cooldown.")
                    alerta_enviada = True

                # Si se envió alerta, guardamos la hora para silenciarla
                if alerta_enviada:
                    last_alert_times[symbol] = current_time

            except Exception as e:
                print(f"Error en {symbol}: {e}")
                continue

        print("⚡ Radar Activo: Escaneando nuevamente en 60 seg...")
        time.sleep(60)

if __name__ == '__main__':
    run_rescue_bot()
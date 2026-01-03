import time
import pandas as pd
import requests
from binance.client import Client
import config  # <--- IMPORTAMOS TU CAJA FUERTE (config.py)

# --- CONEXIÓN SEGURA ---
client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=config.TESTNET_MODE)

# --- 🚑 LISTA DE PACIENTES ---
WATCHLIST = ['DEGENUSDT', 'TRXUSDT', 'WIFUSDT', 'DEXEUSDT', 'ATHUSDT']

# --- ❄️ TIEMPO DE SILENCIO (4 Horas) ---
COOLDOWN_SECONDS = 14400
last_alert_times = {}

# --- TELEGRAM ---
def send_telegram_alert(message):
    try:
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
    # K es rápido, D es lento (media de K), J es volátil
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
        # Pedimos 100 velas para asegurar cálculos correctos
        klines = client.futures_klines(symbol=symbol, interval=interval, limit=100)
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'q', 'n', 'v', 'q2', 'i'])
        df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
        return df
    except:
        return pd.DataFrame()

# --- LÓGICA DE RESCATE (FRANCOTIRADOR V4) ---
def run_rescue_bot():
    print("🚑 Bot de Rescate V4 (Francotirador J+D) Iniciado...")
    send_telegram_alert(f"🚑 Bot V4 ONLINE. Configuración:\nLONG: J<=0 y D<=25\nSHORT: J>=100 y D>=75")

    while True:
        current_time = time.time()

        for symbol in WATCHLIST:
            try:
                # 1. Chequeo de Cooldown
                if symbol in last_alert_times:
                    tiempo_pasado = current_time - last_alert_times[symbol]
                    if tiempo_pasado < COOLDOWN_SECONDS:
                        continue

                # 2. Descargar datos
                df_15m = get_klines_safe(symbol, '15m')
                df_1h = get_klines_safe(symbol, '1h')
                df_4h = get_klines_safe(symbol, '4h')

                if df_4h.empty: continue

                # 3. Indicadores (J y D)
                _, d15, j15 = calculate_kdj(df_15m)
                _, d1h, j1h = calculate_kdj(df_1h)
                _, d4h, j4h = calculate_kdj(df_4h)

                up_4h, low_4h = calculate_bollinger_bands(df_4h)

                # Valores actuales (última vela cerrada)
                j15_v = j15.iloc[-1]; d15_v = d15.iloc[-1]
                j1h_v = j1h.iloc[-1]; d1h_v = d1h.iloc[-1]
                j4h_v = j4h.iloc[-1]; d4h_v = d4h.iloc[-1]
                
                close = df_15m['close'].iloc[-1]
                piso_4h = low_4h.iloc[-1]
                techo_4h = up_4h.iloc[-1]

                alerta_enviada = False

                # --- CONDICIÓN LONG (PISO EXTREMO) ---
                # J <= 0 y D <= 25 en 4H, 1H y 15m
                cond_j_long = (j4h_v <= 0) and (j1h_v <= 0) and (j15_v <= 0)
                cond_d_long = (d4h_v <= 25) and (d1h_v <= 25) and (d15_v <= 25)

                if cond_j_long and cond_d_long:
                    msg = (f"💎 OPORTUNIDAD LONG (Suelo Extremo) en {symbol}\n"
                           f"Precio: {close}\n"
                           f"----------------\n"
                           f"J(4H/1H/15m): {j4h_v:.1f} / {j1h_v:.1f} / {j15_v:.1f}\n"
                           f"D(4H/1H/15m): {d4h_v:.1f} / {d1h_v:.1f} / {d15_v:.1f}\n"
                           f"Soporte BB 4H: {piso_4h:.4f}")
                    send_telegram_alert(msg)
                    print(f"✅ Alerta LONG enviada para {symbol}.")
                    alerta_enviada = True

                # --- CONDICIÓN SHORT (TECHO EXTREMO) ---
                # J >= 100 y D >= 75 en 4H, 1H y 15m
                cond_j_short = (j4h_v >= 100) and (j1h_v >= 100) and (j15_v >= 100)
                cond_d_short = (d4h_v >= 75) and (d1h_v >= 75) and (d15_v >= 75)

                if cond_j_short and cond_d_short:
                    msg = (f"⚠️ OPORTUNIDAD SHORT (Techo Extremo) en {symbol}\n"
                           f"Precio: {close}\n"
                           f"----------------\n"
                           f"J(4H/1H/15m): {j4h_v:.1f} / {j1h_v:.1f} / {j15_v:.1f}\n"
                           f"D(4H/1H/15m): {d4h_v:.1f} / {d1h_v:.1f} / {d15_v:.1f}\n"
                           f"Resistencia BB 4H: {techo_4h:.4f}")
                    send_telegram_alert(msg)
                    print(f"✅ Alerta SHORT enviada para {symbol}.")
                    alerta_enviada = True

                if alerta_enviada:
                    last_alert_times[symbol] = current_time

            except Exception as e:
                print(f"Error en {symbol}: {e}")
                continue

        print("⚡ Radar V4: Escaneando...")
        time.sleep(60)

if __name__ == '__main__':
    run_rescue_bot()

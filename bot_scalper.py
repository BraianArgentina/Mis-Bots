import time
import pandas as pd
import requests
from binance.client import Client
import config  # <--- IMPORTAMOS TU CAJA FUERTE (config.py)

# --- CONEXIÓN SEGURA ---
# Toma las claves y el modo (Testnet False/True) desde tu archivo config.py
client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET, testnet=config.TESTNET_MODE)

# --- CONFIGURACIÓN DEL BOT ---
MIN_VOLUMEN_24H = 500000000 
MIN_DIAS_HISTORIA = 100  

# --- LISTA NEGRA (Exclusiones Manuales) ---
EXCLUDED_SYMBOLS = ['BNXUSDT', 'FISUSDT'] 

# --- FUNCIONES AUXILIARES ---

def send_telegram_alert(message):
    try:
        # Usa el Token y ID desde config.py
        url = f'https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage'
        payload = {'chat_id': config.TELEGRAM_CHAT_ID, 'text': message}
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}")

def log_signal_to_csv(symbol, signal_type, d1, j1, sig1, d3, j3, sig3, d5, j5, sig5):
    from datetime import datetime
    import os
    CSV_FILE = 'kdj_signals.csv'
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    data = {
        'timestamp': timestamp, 'symbol': symbol, 'signal_type': signal_type,
        'D_1m': round(d1, 2), 'J_1m': round(j1, 2),
        'D_3m': round(d3, 2), 'J_3m': round(j3, 2),
        'D_5m': round(d5, 2), 'J_5m': round(j5, 2)
    }
    df = pd.DataFrame([data])
    # En PythonAnywhere es bueno usar try-except para escritura de archivos por si acaso
    try:
        if not os.path.isfile(CSV_FILE):
            df.to_csv(CSV_FILE, index=False)
        else:
            df.to_csv(CSV_FILE, mode='a', header=False, index=False)
    except Exception as e:
        print(f"Error guardando CSV: {e}")

# --- FUNCIÓN VERIFICADORA DE ANTIGÜEDAD ---
def verificar_antiguedad(symbol, min_dias=60):
    try:
        klines = client.futures_klines(symbol=symbol, interval='1d', limit=min_dias)
        if len(klines) < min_dias:
            return False
        return True
    except Exception as e:
        print(f"⚠️ Error verificando antigüedad de {symbol}: {e}")
        return False

# --- INDICADORES ---

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

def calculate_macd(df, fast=12, slow=26, signal=9):
    close = df['close']
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    sig = macd.ewm(span=signal, adjust=False).mean()
    return macd, sig

def calculate_bollinger_bands(df, period=20, std_dev=2):
    sma = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    return upper, lower

# --- FILTRADO ---
def get_liquid_symbols():
    try:
        print("🔍 Obteniendo monedas con alto volumen...")
        tickers = client.futures_ticker()
        liquid_symbols = []

        for t in tickers:
            symbol = t['symbol']
            
            # Filtro básico para evitar errores de tipo
            if 'quoteVolume' not in t: continue
            volumen = float(t['quoteVolume'])

            if symbol in EXCLUDED_SYMBOLS:
                print(f"⛔ {symbol} excluida manualmente.")
                continue

            if symbol.endswith('USDT') and volumen >= MIN_VOLUMEN_24H:
                if verificar_antiguedad(symbol, min_dias=MIN_DIAS_HISTORIA):
                    liquid_symbols.append(symbol)
                else:
                    print(f"🚫 {symbol} descartada: Muy nueva.")

        print(f"✅ Lista Final: {len(liquid_symbols)} monedas seguras")
        return liquid_symbols
    except Exception as e:
        print(f"Error filtrando símbolos: {e}")
        return []

def get_klines_safe(symbol, interval):
    try:
        klines = client.futures_klines(symbol=symbol, interval=interval, limit=50)
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'q', 'n', 'v', 'q2', 'i'])
        df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
        return df
    except:
        return pd.DataFrame()

# --- LÓGICA PRINCIPAL ---

def run_bot():
    print("Iniciando Bot Scalper en PythonAnywhere...")
    # Aviso a Telegram de que el bot revivió (útil si se reinicia el servidor)
    send_telegram_alert("🤖 Bot Scalper (1m/3m/5m) INICIADO en el Servidor.")

    symbols = get_liquid_symbols()

    if not symbols:
        print("Error: No se encontraron símbolos. Reintentando en 60s...")
        time.sleep(60)
        run_bot()

    while True:
        print(f"⏳ Escaneando {len(symbols)} pares...")

        for symbol in symbols:
            try:
                df_1m = get_klines_safe(symbol, '1m')
                df_3m = get_klines_safe(symbol, '3m')
                df_5m = get_klines_safe(symbol, '5m')

                if df_5m.empty or len(df_5m) < 20: continue

                # Cálculos
                _, d1, j1 = calculate_kdj(df_1m)
                _, d3, j3 = calculate_kdj(df_3m)
                _, d5, j5 = calculate_kdj(df_5m)
                _, sig1 = calculate_macd(df_1m)
                _, sig3 = calculate_macd(df_3m)
                _, sig5 = calculate_macd(df_5m)
                upper, lower = calculate_bollinger_bands(df_5m)

                j1_v, d1_v, sig1_v = j1.iloc[-1], d1.iloc[-1], sig1.iloc[-1]
                j3_v, d3_v, sig3_v = j3.iloc[-1], d3.iloc[-1], sig3.iloc[-1]
                j5_v, d5_v, sig5_v = j5.iloc[-1], d5.iloc[-1], sig5.iloc[-1]

                close = df_5m['close'].iloc[-1]
                up_val, low_val = upper.iloc[-1], lower.iloc[-1]

                # --- CONDICIÓN LONG ---
                if (j1_v <= 0 and d1_v <= 25 and sig1_v < 0 and
                    j3_v <= 0 and d3_v <= 25 and sig3_v < 0 and
                    j5_v <= 0 and d5_v <= 25 and sig5_v < 0):

                    dist = ((close - low_val) / low_val) * 100
                    estado = "DENTRO" if close > low_val else "ROMPIENDO"

                    msg = (f"🟢 LONG {symbol}\nPrecio: {close}\nBanda Inf: {low_val:.4f}\n"
                           f"Estado: {estado} ({dist:.2f}%)\n"
                           f"----------------\nJ(1,3,5): {j1_v:.1f}|{j3_v:.1f}|{j5_v:.1f}")
                    send_telegram_alert(msg)
                    log_signal_to_csv(symbol, 'LONG', d1_v, j1_v, sig1_v, d3_v, j3_v, sig3_v, d5_v, j5_v, sig5_v)
                    print(f"🟢 LONG detectado en {symbol}")

                # --- CONDICIÓN SHORT ---
                elif (j1_v >= 100 and d1_v >= 75 and sig1_v > 0 and
                      j3_v >= 100 and d3_v >= 75 and sig3_v > 0 and
                      j5_v >= 100 and d5_v >= 75 and sig5_v > 0):

                    dist = ((close - up_val) / up_val) * 100
                    estado = "DENTRO" if close < up_val else "ROMPIENDO"

                    msg = (f"🔴 SHORT {symbol}\nPrecio: {close}\nBanda Sup: {up_val:.4f}\n"
                           f"Estado: {estado} ({dist:.2f}%)\n"
                           f"----------------\nJ(1,3,5): {j1_v:.1f}|{j3_v:.1f}|{j5_v:.1f}")
                    send_telegram_alert(msg)
                    log_signal_to_csv(symbol, 'SHORT', d1_v, j1_v, sig1_v, d3_v, j3_v, sig3_v, d5_v, j5_v, sig5_v)
                    print(f"🔴 SHORT detectado en {symbol}")

            except Exception:
                continue

        print("Ciclo completado. Esperando 60 seg...")
        # symbols = get_liquid_symbols() # Si quieres que actualice la lista de monedas cada ciclo, descomenta esto.
        time.sleep(60)

if __name__ == '__main__':
    # Ya no hay keep_alive(), vamos directo al grano
    run_bot()
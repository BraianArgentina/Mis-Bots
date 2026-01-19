import time
import requests
import pandas as pd
import sys
import os

# --- IMPORTACIÓN SEGURA ---
try:
    from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
except ImportError:
    print("⚠️ ERROR CRÍTICO: No se encontró 'config.py' o faltan variables.")
    sys.exit()

# --- CONFIGURACIÓN FUTUROS GLOBAL ---
BASE_URL = "https://fapi.binance.com"
MIN_VOLUMEN_24H = 30000000  # 30 Millones
MIN_DIAS_HISTORIA = 100 # Días
EXCLUDED_SYMBOLS = ['USDCUSDT', 'BUSDUSDT', 'USDPUSDT', 'TUSDUSDT', 'DAIUSDT', 'USDUSDT', 'BNXUSDT', 'FISUSDT']

# --- FUNCIONES ---
def get_binance_data(endpoint, params=None):
    try:
        url = BASE_URL + endpoint
        response = requests.get(url, params=params, timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None

def get_liquid_symbols():
    print(f"🔍 Escaneando Mercado (Vol > {MIN_VOLUMEN_24H/1000000}M)...")
    data = get_binance_data("/fapi/v1/ticker/24hr")
    if not data: return []
    
    liquid_symbols = []
    for item in data:
        symbol = item['symbol']
        if symbol in EXCLUDED_SYMBOLS or not symbol.endswith('USDT'): continue
        try:
            if float(item['quoteVolume']) >= MIN_VOLUMEN_24H:
                # Verificación simple de historia para optimizar velocidad
                liquid_symbols.append(symbol)
        except: continue
            
    print(f"✅ Lista: {len(liquid_symbols)} monedas líquidas.")
    return liquid_symbols

def get_klines(symbol, interval, limit=50):
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    raw = get_binance_data("/fapi/v1/klines", params)
    if not raw: return pd.DataFrame()
    df = pd.DataFrame(raw, columns=['timestamp', 'open', 'high', 'low', 'close', 'v', 'ct', 'q', 'n', 'V', 'Q', 'i'])
    return df[['timestamp', 'open', 'high', 'low', 'close']].astype(float)

def send_telegram_alert(message):
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
        requests.post(url, data=payload, timeout=5)
    except: pass

# --- INDICADORES (KDJ + MACD) ---
def bcwsma(series, length, weight):
    result = [series[0]]
    for i in range(1, len(series)):
        result.append((weight * series[i] + (length - weight) * result[-1]) / length)
    return pd.Series(result)

def calculate_kdj(df):
    low = df['low'].rolling(9).min()
    high = df['high'].rolling(9).max()
    rsv = 100 * ((df['close'] - low) / (high - low))
    k = bcwsma(rsv.fillna(50), 3, 1)
    d = bcwsma(k.fillna(50), 3, 1)
    j = 3 * k - 2 * d
    return k, d, j

def calculate_macd(df):
    close = df['close']
    macd = close.ewm(span=12).mean() - close.ewm(span=26).mean()
    sig = macd.ewm(span=9).mean()
    return macd, sig

# --- MAIN ---
def run_bot():
    print("🚀 SCALPER ACTIVO (FUTUROS GLOBAL)")
    symbols = get_liquid_symbols()
    btc_state = 0 

    while True:
        try:
            # BTC CHECK
            btc_df = get_klines('BTCUSDT', '1h', 2)
            if not btc_df.empty:
                btc_chg = ((btc_df['close'].iloc[-1] - btc_df['open'].iloc[-1]) / btc_df['open'].iloc[-1]) * 100
                print(f"⏳ Escaneando... BTC: {btc_chg:.2f}%")
            else:
                btc_chg = 0

            for symbol in symbols:
                try:
                    df_1m = get_klines(symbol, '1m')
                    df_3m = get_klines(symbol, '3m')
                    df_5m = get_klines(symbol, '5m')
                    if len(df_5m) < 20: continue
                    
                    # LOGICA
                    _, d1, j1 = calculate_kdj(df_1m)
                    _, d3, j3 = calculate_kdj(df_3m)
                    _, d5, j5 = calculate_kdj(df_5m)
                    _, sig1 = calculate_macd(df_1m)
                    _, sig3 = calculate_macd(df_3m)
                    _, sig5 = calculate_macd(df_5m)
                    
                    j1, d1, s1 = j1.iloc[-1], d1.iloc[-1], sig1.iloc[-1]
                    j3, d3, s3 = j3.iloc[-1], d3.iloc[-1], sig3.iloc[-1]
                    j5, d5, s5 = j5.iloc[-1], d5.iloc[-1], sig5.iloc[-1]
                    price = df_5m['close'].iloc[-1]
                    
                    # LONG
                    if (btc_chg > -1.2 and j1<0 and d1<25 and s1<0 and j3<0 and d3<25 and s3<0 and j5<0 and d5<25 and s5<0):
                        msg = f"🟢 LONG {symbol}\nPrecio: {price}\nJ: {j1:.1f}|{j3:.1f}|{j5:.1f}"
                        print(msg)
                        send_telegram_alert(msg)
                    
                    # SHORT
                    elif (btc_chg < 1.2 and j1>100 and d1>75 and s1>0 and j3>100 and d3>75 and s3>0 and j5>100 and d5>75 and s5>0):
                        msg = f"🔴 SHORT {symbol}\nPrecio: {price}\nJ: {j1:.1f}|{j3:.1f}|{j5:.1f}"
                        print(msg)
                        send_telegram_alert(msg)

                except: continue
            time.sleep(60)
        except KeyboardInterrupt:
            print("\n🛑 Fin.")
            sys.exit()
        except:
            time.sleep(10)

if __name__ == '__main__':
    run_bot()

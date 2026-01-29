import time
import requests
import pandas as pd
import sys
import os

# --- IMPORTACIÓN SEGURA ---
try:
    from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
except ImportError:
    print("⚠️ ERROR CRÍTICO: No se encontró 'config.py'. Asegúrate de tenerlo en la carpeta.")
    sys.exit()

# --- CONFIGURACIÓN FUTUROS GLOBAL ---
BASE_URL = "https://fapi.binance.com"
MIN_VOLUMEN_24H = 30000000  # 30 Millones
MIN_ANTIGUEDAD_DIAS = 100   # Mínimo 100 días de vida
EXCLUDED_SYMBOLS = ['USDCUSDT', 'BUSDUSDT', 'USDPUSDT', 'TUSDUSDT', 'DAIUSDT', 'USDUSDT', 'BNXUSDT', 'FISUSDT', 'PAXGUSDT']

# --- FUNCIONES DE CONEXIÓN ---
def get_binance_data(endpoint, params=None):
    try:
        url = BASE_URL + endpoint
        response = requests.get(url, params=params, timeout=5) # Timeout corto para velocidad
        return response.json() if response.status_code == 200 else None
    except:
        return None

def get_liquid_symbols():
    print(f"🔍 Escaneando Mercado (Vol > {MIN_VOLUMEN_24H/1000000}M y Edad > {MIN_ANTIGUEDAD_DIAS} días)...")
    
    # 1. Obtenemos datos de volumen
    ticker_data = get_binance_data("/fapi/v1/ticker/24hr")
    # 2. Obtenemos información de la moneda (para saber su fecha de creación)
    exchange_info = get_binance_data("/fapi/v1/exchangeInfo")
    
    if not ticker_data or not exchange_info: 
        return []
    
    # Mapa de fechas de creación {simbolo: fecha_ms}
    onboard_dates = {item['symbol']: item['onboardDate'] for item in exchange_info['symbols']}
    
    # Calcular fecha límite en milisegundos
    limit_time_ms = (time.time() * 1000) - (MIN_ANTIGUEDAD_DIAS * 24 * 60 * 60 * 1000)

    liquid_symbols = []
    
    for item in ticker_data:
        symbol = item['symbol']
        
        # Filtros básicos
        if symbol in EXCLUDED_SYMBOLS or not symbol.endswith('USDT'): continue
        
        try:
            # 1. Filtro de Volumen
            if float(item['quoteVolume']) < MIN_VOLUMEN_24H:
                continue

            # 2. Filtro de Antigüedad (NUEVO)
            # Si no encontramos la fecha, asumimos que es nueva y la saltamos por seguridad
            creation_date = onboard_dates.get(symbol, float('inf')) 
            if creation_date > limit_time_ms:
                # Si la fecha de creación es MAYOR al límite, significa que es más nueva (nació después)
                continue 

            liquid_symbols.append(symbol)

        except: continue
            
    print(f"✅ Lista filtrada: {len(liquid_symbols)} monedas aptas.")
    return liquid_symbols

def get_klines(symbol, interval, limit=50):
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    raw = get_binance_data("/fapi/v1/klines", params)
    if not raw: return pd.DataFrame()
    
    # Columnas básicas para velocidad
    df = pd.DataFrame(raw, columns=['timestamp', 'open', 'high', 'low', 'close', 'v', 'ct', 'q', 'n', 'V', 'Q', 'i'])
    return df[['open', 'high', 'low', 'close']].astype(float)

def send_telegram_alert(message):
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
        requests.post(url, data=payload, timeout=5)
    except: pass

# --- INDICADORES TÉCNICOS ---
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

def calculate_bollinger(df, period=20, std_dev=2):
    # Usamos la data de 5m para las bandas referenciales
    sma = df['close'].rolling(period).mean()
    std = df['close'].rolling(period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    return upper, lower

# --- MAIN LOOP ---
def run_bot():
    print("🚀 SCALPER ACTIVO (V8.0 - Filtro 100 Días)")
    
    while True:
        try:
            # Actualizamos la lista en cada vuelta grande por si el volumen cambia
            symbols = get_liquid_symbols()

            # 1. Chequeo BTC (Termómetro del mercado)
            btc_df = get_klines('BTCUSDT', '1h', 2)
            if not btc_df.empty:
                btc_chg = ((btc_df['close'].iloc[-1] - btc_df['open'].iloc[-1]) / btc_df['open'].iloc[-1]) * 100
                print(f"⏳ BTC 1h: {btc_chg:.2f}% | Analizando {len(symbols)} monedas...")
            else:
                btc_chg = 0

            # 2. Escaneo de Monedas
            for symbol in symbols:
                try:
                    # Obtenemos Dataframes
                    df_1m = get_klines(symbol, '1m', 35)
                    df_3m = get_klines(symbol, '3m', 35)
                    df_5m = get_klines(symbol, '5m', 35)
                    
                    # Necesitamos data suficiente
                    if len(df_5m) < 25: continue
                    
                    # Obtenemos cambio 1H de la moneda (para el reporte)
                    df_1h_coin = get_klines(symbol, '1h', 2)
                    coin_chg_1h = 0.0
                    if not df_1h_coin.empty:
                          coin_chg_1h = ((df_1h_coin['close'].iloc[-1] - df_1h_coin['open'].iloc[-1]) / df_1h_coin['open'].iloc[-1]) * 100

                    # --- CÁLCULOS ---
                    k1, d1, j1 = calculate_kdj(df_1m)
                    k3, d3, j3 = calculate_kdj(df_3m)
                    k5, d5, j5 = calculate_kdj(df_5m)
                    _, sig1 = calculate_macd(df_1m)
                    _, sig3 = calculate_macd(df_3m)
                    _, sig5 = calculate_macd(df_5m)
                    
                    # Bandas Bollinger (Usamos 5m como referencia visual)
                    upper_bb, lower_bb = calculate_bollinger(df_5m)
                    
                    # Valores actuales (última vela cerrada o actual)
                    j_val = [j1.iloc[-1], j3.iloc[-1], j5.iloc[-1]]
                    d_val = [d1.iloc[-1], d3.iloc[-1], d5.iloc[-1]]
                    s_val = [sig1.iloc[-1], sig3.iloc[-1], sig5.iloc[-1]]
                    
                    price = df_5m['close'].iloc[-1]
                    up_band = upper_bb.iloc[-1]
                    low_band = lower_bb.iloc[-1]
                    
                    signal_type = None

                    # --- LÓGICA DE ENTRADA ---
                    # LONG: BTC estable/subiendo + J negativo + D bajo + MACD negativo (sobreventa)
                    if (btc_chg > -1.2 and 
                        j_val[0]<0 and d_val[0]<25 and s_val[0]<0 and 
                        j_val[1]<0 and d_val[1]<25 and s_val[1]<0 and 
                        j_val[2]<0 and d_val[2]<25 and s_val[2]<0):
                        signal_type = "LONG"
                        ref_band = low_band
                        band_name = "Inf"

                    # SHORT: BTC estable/bajando + J alto + D alto + MACD positivo (sobrecompra)
                    elif (btc_chg < 1.2 and 
                          j_val[0]>100 and d_val[0]>75 and s_val[0]>0 and 
                          j_val[1]>100 and d_val[1]>75 and s_val[1]>0 and 
                          j_val[2]>100 and d_val[2]>75 and s_val[2]>0):
                        signal_type = "SHORT"
                        ref_band = up_band
                        band_name = "Sup"

                    # --- ENVÍO DE ALERTA ---
                    if signal_type:
                        # Calcular distancia a la banda
                        dist_pct = ((price - ref_band) / ref_band) * 100
                        state_str = f"ROMPIENDO ({abs(dist_pct):.2f}%)" if (signal_type=="LONG" and price<ref_band) or (signal_type=="SHORT" and price>ref_band) else f"Cercano ({abs(dist_pct):.2f}%)"
                        
                        icon = "🟢" if signal_type == "LONG" else "🔴"
                        
                        msg = (
                            f"{icon} {signal_type} {symbol}\n"
                            f"Precio: {price}\n"
                            f"Banda {band_name} (5m): {ref_band:.4f}\n"
                            f"Estado: {state_str}\n"
                            f"Cambio 1h: {coin_chg_1h:.2f}%\n"
                            f"----------------\n"
                            f"J(1,3,5): {j_val[0]:.1f}|{j_val[1]:.1f}|{j_val[2]:.1f}\n"
                            f"D(1,3,5): {d_val[0]:.1f}|{d_val[1]:.1f}|{d_val[2]:.1f}"
                        )
                        print(f"\n{msg}\n")
                        send_telegram_alert(msg)
                        time.sleep(2) # Pequeña pausa para no saturar si salen varias juntas

                except Exception as e:
                    continue
            
            # Pausa entre ciclos de escaneo completo
            print("💤 Esperando 60s...")
            time.sleep(60)

        except KeyboardInterrupt:
            print("\n🛑 Fin.")
            sys.exit()
        except:
            time.sleep(10)

if __name__ == '__main__':
    run_bot()

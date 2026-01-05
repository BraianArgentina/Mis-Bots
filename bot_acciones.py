import time
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import pytz
import config_acciones as config 

# ==========================================
# ⚙️ AJUSTES DE TIEMPO
# ==========================================
COOLDOWN_SECONDS = 10800  # 3 Horas
SLEEP_TIME = 180          # 3 Minutos

# ==========================================
# 🧠 FUNCIONES AUXILIARES
# ==========================================

def send_telegram(msg):
    try:
        url = f'https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage'
        payload = {'chat_id': config.TELEGRAM_CHAT_ID, 'text': msg}
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}")

def mercado_abierto():
    """Devuelve True si es Lunes-Viernes entre 11:00 y 17:00 (Hora Arg)"""
    tz = pytz.timezone('America/Argentina/Buenos_Aires')
    now = datetime.now(tz)
    
    if now.weekday() > 4: return False 
    if 11 <= now.hour < 17: return True
    return False

def bcwsma(series, length, weight):
    result = []
    for i in range(len(series)):
        if i == 0: result.append(series[i])
        else:
            prev = result[-1]
            val = (weight * series[i] + (length - weight) * prev) / length
            result.append(val)
    return pd.Series(result, index=series.index)

def calculate_kdj(df):
    low = df['Low'].rolling(9).min()
    high = df['High'].rolling(9).max()
    rsv = 100 * ((df['Close'] - low) / (high - low))
    
    k = bcwsma(rsv.fillna(50), 3, 1)
    d = bcwsma(k.fillna(50), 3, 1)
    j = 3 * k - 2 * d
    return k, d, j

# ==========================================
# 🏥 HEALTH CHECK
# ==========================================
def validar_lista_activos(watchlist_full):
    print("🏥 Iniciando chequeo de salud de tickers...")
    bad_tickers = []
    
    for symbol in watchlist_full.keys():
        try:
            tik = yf.Ticker(symbol)
            df = tik.history(period="1d")
            
            if df.empty:
                bad_tickers.append(symbol)
                print(f"❌ Error: {symbol} no devuelve datos.")
            else:
                print(f"✅ OK: {symbol}", end="\r") 
                
        except Exception:
            bad_tickers.append(symbol)
        
        time.sleep(0.1)
        
    print(f"\n✅ Chequeo finalizado.")
    
    if bad_tickers:
        msg = f"⚠️ REPORT DE ERRORES ⚠️\nIgnorados por fallo en Yahoo: {', '.join(bad_tickers)}"
        send_telegram(msg)
        return bad_tickers
    else:
        return []

# ==========================================
# 🚀 MOTOR PRINCIPAL
# ==========================================

def run_acciones_bot():
    print("👔 Bot Acciones (Modo Francotirador) Iniciado...")
    
    # --- 1. LÓGICA DEL INTERRUPTOR ---
    # Primero cargamos SOLO el portfolio (siempre activo)
    full_watchlist = {}
    
    # Agregamos portfolio a la lista de vigilancia
    for t in config.PORTFOLIO:
        # Buscamos el nombre bonito en el diccionario, si no existe usamos el ticker
        nombre = config.WATCHLIST_DICT.get(t, t) 
        full_watchlist[t] = nombre

    # Ahora miramos el interruptor del config
    if config.BUSCAR_NUEVAS_ENTRADAS:
        print("🟢 MODO EXPANSIVO: Buscando nuevas oportunidades (Watchlist completa).")
        # Agregamos el resto de la lista gigante
        for t, nombre in config.WATCHLIST_DICT.items():
            if t not in full_watchlist:
                full_watchlist[t] = nombre
    else:
        print("🟠 MODO DEFENSA: Solo vigilando Portfolio (Recompra/Venta).")

    # --- 2. Validar Listas ---
    bad_tickers = validar_lista_activos(full_watchlist)
    for bad in bad_tickers:
        if bad in full_watchlist:
            del full_watchlist[bad]
            
    send_telegram(f"👔 Bot Acciones ONLINE.\nVigilando {len(full_watchlist)} activos.\nModo Nuevas Entradas: {'ON' if config.BUSCAR_NUEVAS_ENTRADAS else 'OFF'}")
    
    last_alerts = {} 

    while True:
        if not mercado_abierto():
            print(f"💤 Mercado Cerrado ({datetime.now().strftime('%H:%M')}). Durmiendo 30 min...")
            time.sleep(1800) 
            continue

        print("⚡ Escaneando mercado...")

        # Recarga config (Para cambios en vivo)
        import importlib
        importlib.reload(config)
        
        # OJO: Si cambias el interruptor en caliente, la lista 'full_watchlist'
        # NO se actualiza sola dentro del while (requiere reiniciar bot para cambiar modo).
        # Pero sí detecta si mueves acciones dentro/fuera del portfolio.

        for symbol, name in full_watchlist.items():
            try:
                if symbol in last_alerts:
                    if time.time() - last_alerts[symbol] < COOLDOWN_SECONDS:
                        continue

                ticker_obj = yf.Ticker(symbol)
                df = ticker_obj.history(period="1mo", interval="1h")
                time.sleep(1.5) 

                if df.empty or len(df) < 20: continue

                k, d, j = calculate_kdj(df)
                j_curr = j.iloc[-1]
                d_curr = d.iloc[-1]
                precio = df['Close'].iloc[-1]
                
                # --- LÓGICA ---
                
                # COMPRA (Suelo)
                if j_curr <= 0 and d_curr <= 25:
                    
                    if symbol in config.PORTFOLIO:
                        # ESCENARIO B: RECOMPRA (Siempre activo)
                        msg = (f"📉 OPORTUNIDAD RECOMPRA: {name} ({symbol})\n"
                               f"Promediar a la baja (USD {precio:.2f})\n"
                               f"----------------\n"
                               f"J: {j_curr:.2f} | D: {d_curr:.2f}")
                        print(f"✅ Recompra: {symbol}")
                        send_telegram(msg)
                        last_alerts[symbol] = time.time()
                        
                    elif config.BUSCAR_NUEVAS_ENTRADAS:
                        # ESCENARIO A: NUEVA ENTRADA (Solo si el interruptor es True)
                        msg = (f"💎 NUEVA ENTRADA: {name} ({symbol})\n"
                               f"Precio Entrada: USD {precio:.2f})\n"
                               f"----------------\n"
                               f"J: {j_curr:.2f} | D: {d_curr:.2f}")
                        print(f"✅ Entrada: {symbol}")
                        send_telegram(msg)
                        last_alerts[symbol] = time.time()

                # VENTA (Techo)
                elif j_curr >= 100 and d_curr >= 75:
                    
                    if symbol in config.PORTFOLIO:
                        # ESCENARIO C: VENTA (Siempre activo)
                        msg = (f"💰 TOMA DE GANANCIAS: {name} ({symbol})\n"
                               f"Vender ahora (USD {precio:.2f})\n"
                               f"----------------\n"
                               f"J: {j_curr:.2f} | D: {d_curr:.2f}")
                        send_telegram(msg)
                        print(f"✅ Venta: {symbol}")
                        last_alerts[symbol] = time.time()
                    
            except Exception:
                continue
        
        print(f"⏳ Ciclo terminado. Esperando {SLEEP_TIME/60} minutos...")
        time.sleep(SLEEP_TIME)

if __name__ == "__main__":
    run_acciones_bot()

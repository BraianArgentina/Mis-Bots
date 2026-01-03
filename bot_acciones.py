import time
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime
import pytz
import config_acciones as config # <--- IMPORTA TUS LISTAS Y CLAVES

# ==========================================
# ⚙️ AJUSTES DE TIEMPO
# ==========================================
# Respawn (Silencio) de alerta: 3 HORAS (10800 seg)
# Razón: Mercado de 6hs. Permite una alerta a la mañana y otra a la tarde.
COOLDOWN_SECONDS = 10800 

# Descanso entre vueltas: 3 MINUTOS (180 seg)
SLEEP_TIME = 180

# ==========================================
# 🧠 LÓGICA MATEMÁTICA
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
    
    # 0=Lunes, 4=Viernes, 5=Sabado, 6=Domingo
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
    # KDJ Estándar (9,3,3)
    low = df['Low'].rolling(9).min()
    high = df['High'].rolling(9).max()
    rsv = 100 * ((df['Close'] - low) / (high - low))
    
    k = bcwsma(rsv.fillna(50), 3, 1)
    d = bcwsma(k.fillna(50), 3, 1)
    j = 3 * k - 2 * d
    return k, d, j

# ==========================================
# 🚀 MOTOR PRINCIPAL
# ==========================================

def run_acciones_bot():
    print("👔 Bot Acciones (Modo Francotirador) Iniciado...")
    print(f"⏱️ Config: Cooldown {COOLDOWN_SECONDS/3600}hs | Loop {SLEEP_TIME/60}min")
    
    send_telegram("👔 Bot Acciones ONLINE.\nEsperando apertura (11-17hs).")
    
    last_alerts = {} 

    while True:
        # 1. Chequeo de Horario
        if not mercado_abierto():
            print(f"💤 Mercado Cerrado ({datetime.now().strftime('%H:%M')}). Durmiendo 30 min...")
            time.sleep(1800) 
            continue

        print("⚡ Escaneando mercado (Yahoo Finance)...")

        # Recarga config por si hiciste cambios en github/termius
        import importlib
        importlib.reload(config) 
        
        # Unificamos listas
        full_watchlist = config.WATCHLIST_DICT.copy()
        for t in config.PORTFOLIO:
            if t not in full_watchlist:
                full_watchlist[t] = t

        for symbol, name in full_watchlist.items():
            try:
                # 2. Cooldown (3 Horas)
                if symbol in last_alerts:
                    if time.time() - last_alerts[symbol] < COOLDOWN_SECONDS:
                        continue

                # 3. Descarga de datos
                # NOTA: Yahoo Finance puede bloquear si vamos muy rápido.
                ticker_obj = yf.Ticker(symbol)
                df = ticker_obj.history(period="1mo", interval="1h")
                
                # --- PAUSA DE CORTESÍA ---
                # Dormimos 1 segundo entre acciones para no saturar a Yahoo
                time.sleep(1) 

                if df.empty or len(df) < 20: continue

                # 4. Cálculos
                k, d, j = calculate_kdj(df)
                j_curr = j.iloc[-1]
                d_curr = d.iloc[-1]
                precio = df['Close'].iloc[-1]
                
                # 5. Lógica Francotirador (J<=0 y D<=25)
                
                # --- A y B: COMPRA (Suelo) ---
                if j_curr <= 0 and d_curr <= 25:
                    
                    if symbol in config.PORTFOLIO:
                        # ESCENARIO B: RECOMPRA
                        msg = (f"📉 OPORTUNIDAD RECOMPRA: {name} ({symbol})\n"
                               f"Promediar a la baja (USD {precio:.2f})\n"
                               f"----------------\n"
                               f"J: {j_curr:.2f} | D: {d_curr:.2f}")
                        print(f"✅ Recompra: {symbol}")
                    else:
                        # ESCENARIO A: NUEVA ENTRADA
                        msg = (f"💎 NUEVA ENTRADA: {name} ({symbol})\n"
                               f"Precio Entrada: USD {precio:.2f})\n"
                               f"----------------\n"
                               f"J: {j_curr:.2f} | D: {d_curr:.2f}")
                        print(f"✅ Entrada: {symbol}")
                    
                    send_telegram(msg)
                    last_alerts[symbol] = time.time()

                # --- C: VENTA (Techo) ---
                elif j_curr >= 100 and d_curr >= 75:
                    
                    if symbol in config.PORTFOLIO:
                        msg = (f"💰 TOMA DE GANANCIAS: {name} ({symbol})\n"
                               f"Vender ahora (USD {precio:.2f})\n"
                               f"----------------\n"
                               f"J: {j_curr:.2f} | D: {d_curr:.2f}")
                        send_telegram(msg)
                        print(f"✅ Venta: {symbol}")
                        last_alerts[symbol] = time.time()
                    
            except Exception as e:
                # print(f"Error leve en {symbol}: {e}")
                continue
        
        print(f"⏳ Ciclo terminado. Esperando {SLEEP_TIME/60} minutos...")
        time.sleep(SLEEP_TIME)

if __name__ == "__main__":
    run_acciones_bot()

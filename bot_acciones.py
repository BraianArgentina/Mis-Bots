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
# Cooldown: Tiempo que el bot ignora un activo tras avisar (3 Horas)
COOLDOWN_SECONDS = 10800  
# Sleep Loop: Descanso al terminar de revisar toda la lista (3 Minutos)
SLEEP_TIME = 180          

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
    # Fórmula KDJ Estándar (9,3,3)
    low = df['Low'].rolling(9).min()
    high = df['High'].rolling(9).max()
    rsv = 100 * ((df['Close'] - low) / (high - low))
    
    k = bcwsma(rsv.fillna(50), 3, 1)
    d = bcwsma(k.fillna(50), 3, 1)
    j = 3 * k - 2 * d
    return k, d, j

# ==========================================
# 🏥 HEALTH CHECK (Validación de Tickers)
# ==========================================
def validar_lista_activos(watchlist_full):
    print("🏥 Iniciando chequeo de salud de tickers... (Esto toma unos segundos)")
    bad_tickers = []
    
    # Probamos descargar 1 día de datos para ver si existe
    for symbol in watchlist_full.keys():
        try:
            tik = yf.Ticker(symbol)
            # Pedimos 1 día para verificar existencia sin gastar recursos
            df = tik.history(period="1d")
            
            if df.empty:
                bad_tickers.append(symbol)
                print(f"❌ Error: {symbol} no devuelve datos.")
            else:
                print(f"✅ OK: {symbol}", end="\r") 
                
        except Exception:
            bad_tickers.append(symbol)
            print(f"❌ Error Crítico: {symbol}")
        
        time.sleep(0.1) # Pequeña pausa técnica
        
    print(f"\n✅ Chequeo finalizado.")
    
    if bad_tickers:
        msg = "⚠️ REPORT DE ERRORES ⚠️\nLos siguientes tickers NO funcionan en Yahoo Finance y serán ignorados:\n\n"
        msg += ", ".join(bad_tickers)
        msg += "\n\nPor favor revisa config_acciones.py cuando puedas."
        send_telegram(msg)
        return bad_tickers
    else:
        print("🎉 Todos los tickers están operativos.")
        return []

# ==========================================
# 🚀 MOTOR PRINCIPAL
# ==========================================

def run_acciones_bot():
    print("👔 Bot Acciones (Modo Francotirador) Iniciado...")
    print(f"⏱️ Config: Cooldown {COOLDOWN_SECONDS/3600}hs | Loop {SLEEP_TIME/60}min")
    
    # 1. Unificar Listas desde Config
    # (Al estar fuera del loop, obliga a reiniciar el bot para aplicar cambios)
    full_watchlist = config.WATCHLIST_DICT.copy()
    for t in config.PORTFOLIO:
        if t not in full_watchlist:
            full_watchlist[t] = t
            
    # 2. Ejecutar Health Check (Reporta errores al Telegram)
    bad_tickers = validar_lista_activos(full_watchlist)
    
    # Eliminamos los malos de la lista local
    for bad in bad_tickers:
        if bad in full_watchlist:
            del full_watchlist[bad]
            
    send_telegram(f"👔 Bot Acciones ONLINE.\nVigilando {len(full_watchlist)} activos válidos.\nEsperando apertura (11-17hs).")
    
    last_alerts = {} 

    while True:
        # 3. Chequeo de Horario
        if not mercado_abierto():
            print(f"💤 Mercado Cerrado ({datetime.now().strftime('%H:%M')}). Durmiendo 30 min...")
            time.sleep(1800) 
            continue

        print("⚡ Escaneando mercado (Yahoo Finance)...")

        for symbol, name in full_watchlist.items():
            try:
                # 4. Cooldown Global
                if symbol in last_alerts:
                    if time.time() - last_alerts[symbol] < COOLDOWN_SECONDS:
                        continue

                # 5. Descarga de datos
                ticker_obj = yf.Ticker(symbol)
                df = ticker_obj.history(period="1mo", interval="1h")
                
                # Pausa de cortesía para Yahoo (1.5 seg)
                time.sleep(1.5) 

                if df.empty or len(df) < 20: continue

                # 6. Cálculos Matemáticos
                k, d, j = calculate_kdj(df)
                j_curr = j.iloc[-1]
                d_curr = d.iloc[-1]
                precio = df['Close'].iloc[-1]
                
                # 7. Lógica de Decisión (Francotirador)
                
                # --- ESCENARIO A y B: COMPRA (Suelo) ---
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
                               f"Precio Entrada: USD {precio:.2f}\n"
                               f"----------------\n"
                               f"J: {j_curr:.2f} | D: {d_curr:.2f}")
                        print(f"✅ Entrada: {symbol}")
                    
                    send_telegram(msg)
                    last_alerts[symbol] = time.time()

                # --- ESCENARIO C: VENTA (Techo) ---
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
                # Si falla algo leve, seguimos
                continue
        
        print(f"⏳ Ciclo terminado. Esperando {SLEEP_TIME/60} minutos...")
        time.sleep(SLEEP_TIME)

if __name__ == "__main__":
    run_acciones_bot()

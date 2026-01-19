import time
import pandas as pd
import yfinance as yf
import requests
import schedule
from datetime import datetime
import pytz
import config_acciones as config 

# ==========================================
# ⚙️ CONFIGURACIÓN GENERAL
# ==========================================
TIMEZONE = pytz.timezone('America/Argentina/Cordoba')

# COOLDOWN: 10800 segundos = 3 HORAS
# El bot no repetirá la alerta del MISMO activo en menos de este tiempo.
COOLDOWN_SECONDS = 10800  

# ==========================================
# 🧠 FUNCIONES AUXILIARES
# ==========================================

def send_telegram(msg):
    try:
        url = f'https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage'
        payload = {'chat_id': config.TELEGRAM_CHAT_ID, 'text': msg, 'parse_mode': 'Markdown'}
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}")

def mercado_abierto():
    """Devuelve True si es Lunes-Viernes entre 11:00 y 17:00 (Hora Arg)"""
    now = datetime.now(TIMEZONE)
    if now.weekday() > 4: return False # Sábado (5) y Domingo (6) OFF
    if 11 <= now.hour < 17: return True
    return False

def bcwsma(series, length, weight):
    # Media móvil suavizada para el cálculo preciso del KDJ
    result = []
    for i in range(len(series)):
        if i == 0: result.append(series[i])
        else:
            prev = result[-1]
            val = (weight * series[i] + (length - weight) * prev) / length
            result.append(val)
    return pd.Series(result, index=series.index)

def calculate_kdj(df):
    try:
        low = df['Low'].rolling(9).min()
        high = df['High'].rolling(9).max()
        rsv = 100 * ((df['Close'] - low) / (high - low))
        k = bcwsma(rsv.fillna(50), 3, 1)
        d = bcwsma(k.fillna(50), 3, 1)
        j = 3 * k - 2 * d
        return k, d, j
    except:
        return None, None, None

def get_last_kdj(df):
    """Calcula KDJ completo y devuelve solo los últimos valores J y D"""
    if df.empty or len(df) < 20: return None, None
    k, d, j = calculate_kdj(df)
    if k is None: return None, None
    return j.iloc[-1], d.iloc[-1]

# ==========================================
# 🎯 TAREA PRINCIPAL: ESCÁNER TRIPLE CONFLUENCIA (ASIMÉTRICO)
# ==========================================
last_alerts = {} 

def job_escanear_oportunidades():
    # 1. Chequeo de horario
    if not mercado_abierto():
        return

    print(f"⚡ Escaneando (Compra Estricta / Venta Calibrada)... ({datetime.now(TIMEZONE).strftime('%H:%M')})")
    
    # 2. Preparar lista de activos (Portfolio + Watchlist)
    full_watchlist = {}
    port_items = config.PORTFOLIO.items() if isinstance(config.PORTFOLIO, dict) else [(t, t) for t in config.PORTFOLIO]
    for t, n in port_items: full_watchlist[t] = n
    
    if config.BUSCAR_NUEVAS_ENTRADAS:
        for t, n in config.WATCHLIST_DICT.items():
            if t not in full_watchlist: full_watchlist[t] = n

    # 3. Analizar cada activo
    for symbol, name in full_watchlist.items():
        try:
            # --- FILTRO 1: COOLDOWN ---
            # Si ya avisamos de este activo hace menos de 3 horas, pasamos al siguiente
            if symbol in last_alerts:
                if time.time() - last_alerts[symbol] < COOLDOWN_SECONDS:
                    continue

            ticker_obj = yf.Ticker(symbol)
            
            # --- OBTENER DATOS (Los 3 timeframes) ---
            
            # A) Datos Intradía (1H)
            df_1h = ticker_obj.history(period="1mo", interval="1h")
            if df_1h.empty: continue
            
            # B) Construir 4H desde 1H (Resampling matemático)
            agg_dict = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
            try:
                df_4h = df_1h.resample('4h').agg(agg_dict).dropna()
            except:
                continue

            # C) Datos Diario (1D)
            df_1d = ticker_obj.history(period="6mo", interval="1d")
            if df_1d.empty: continue

            # --- CÁLCULO DE INDICADORES ---
            j1, d1 = get_last_kdj(df_1h)
            j4, d4 = get_last_kdj(df_4h)
            jd, dd = get_last_kdj(df_1d)

            # Si falla algún cálculo, abortamos este activo
            if j1 is None or j4 is None or jd is None: continue

            precio = df_1h['Close'].iloc[-1]

            # --- LÓGICA DE DECISIÓN (ASIMÉTRICA) ---
            msg = ""
            tipo = ""

            # -----------------------------------------------------------
            # 1. CONDICIÓN DE COMPRA (ESTRICTA) - SIN CAMBIOS
            # Regla: Todos en suelo (J<=0, D<=25)
            # -----------------------------------------------------------
            if (j1 <= 0 and d1 <= 25) and \
               (j4 <= 0 and d4 <= 25) and \
               (jd <= 0 and dd <= 25):
                
                if symbol in config.PORTFOLIO:
                    tipo = "RECOMPRA MAESTRA 📉🔥"
                    msg = "Suelo confirmado en 1H, 4H y Diario."
                elif config.BUSCAR_NUEVAS_ENTRADAS:
                    tipo = "ENTRADA DE ORO 💎🔥"
                    msg = "Triple alineación técnica (Suelo Total)."

            # -----------------------------------------------------------
            # 2. CONDICIÓN DE VENTA (CALIBRADA / CASCADA) - NUEVA LÓGICA V4
            # Regla ajustada:
            # 1H: J>=100, D>=75 (Gatillo rápido)
            # 4H: J>=95,  D>=70 (Confirmación fuerte)
            # 1D: J>=90,  D>=65 (Contexto de techo)
            # -----------------------------------------------------------
            elif (j1 >= 95 and d1 >= 70) and \
                 (j4 >= 90  and d4 >= 65) and \
                 (jd >= 80  and dd >= 60):
                
                if symbol in config.PORTFOLIO:
                    tipo = "TOMA DE GANANCIAS 💰⚡"
                    msg = "Techo confirmado: 1H(Extremo) + 4H(Alto) + 1D(Zona Alta)."

            # SI SE CUMPLE ALGUNA, ENVIAR AVISO
            if msg:
                alerta = (f"🚨 **{tipo}**\n"
                          f"Ticker: {symbol} ({name})\n"
                          f"Precio: ${precio:.2f}\n"
                          f"----------------\n"
                          f"📊 **KDJ CASCADA:**\n"
                          f"• 1H: J={j1:.0f} | D={d1:.0f}\n"
                          f"• 4H: J={j4:.0f} | D={d4:.0f}\n"
                          f"• 1D: J={jd:.0f} | D={dd:.0f}\n"
                          f"----------------\n"
                          f"💡 {msg}")
                
                send_telegram(alerta)
                print(f"✅ ALERTA ENVIADA: {symbol}")
                
                # Activamos el Cooldown de 3 horas para este ticker
                last_alerts[symbol] = time.time()
                time.sleep(1)

        except Exception as e:
            continue

# ==========================================
# 🔔 AVISOS MERCADO
# ==========================================
def job_avisos_mercado():
    now = datetime.now(TIMEZONE)
    hora = now.strftime("%H:%M")
    if now.weekday() > 4: return

    if hora == "11:00":
        send_telegram(f"🔔 **MERCADO ABIERTO**\nEstrategia: Compra Estricta / Venta Calibrada.")
    if hora == "17:00":
        send_telegram("🔕 **MERCADO CERRADO**\nFin de la jornada.")

# ==========================================
# 🚀 MOTOR PRINCIPAL
# ==========================================
if __name__ == "__main__":
    print("🤖 BOT ACCIONES (V4 CALIBRADO) INICIADO")
    send_telegram(f"🤖 **BOT ACTIVO V4**\nEstrategia: Compra Estricta / Venta Calibrada\nCooldown: 3 Horas.")
    
    # Escaneo cada 5 minutos
    schedule.every(5).minutes.do(job_escanear_oportunidades)
    schedule.every(1).minutes.do(job_avisos_mercado)

    if mercado_abierto():
        job_escanear_oportunidades()

    while True:
        schedule.run_pending()
        time.sleep(1)

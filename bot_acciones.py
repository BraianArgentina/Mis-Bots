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
COOLDOWN_SECONDS = 10800  # 3 Horas entre alertas del mismo activo para no ser pesado

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
    if now.weekday() > 4: return False # Fines de semana OFF
    if 11 <= now.hour < 17: return True
    return False

def bcwsma(series, length, weight):
    # Media móvil suavizada para el KDJ
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

# ==========================================
# 🎯 TAREA PRINCIPAL: ESCÁNER SNIPER (KDJ)
# ==========================================
last_alerts = {} 

def job_escanear_oportunidades():
    if not mercado_abierto():
        # Si está cerrado, no hacemos nada ni imprimimos nada para no llenar el log
        return

    print(f"⚡ Escaneando mercado... ({datetime.now(TIMEZONE).strftime('%H:%M')})")
    
    # 1. Preparar lista
    full_watchlist = {}
    
    # Siempre vigilamos el Portfolio
    port_items = config.PORTFOLIO.items() if isinstance(config.PORTFOLIO, dict) else [(t, t) for t in config.PORTFOLIO]
    for t, n in port_items: full_watchlist[t] = n

    # Si el modo "Buscar Nuevas" está activo, agregamos el resto
    if config.BUSCAR_NUEVAS_ENTRADAS:
        for t, n in config.WATCHLIST_DICT.items():
            if t not in full_watchlist: full_watchlist[t] = n

    # 2. Analizar cada activo
    for symbol, name in full_watchlist.items():
        try:
            # Control de Cooldown
            if symbol in last_alerts:
                if time.time() - last_alerts[symbol] < COOLDOWN_SECONDS:
                    continue

            ticker_obj = yf.Ticker(symbol)
            # Bajamos datos de 1 mes, velas de 1 hora
            df = ticker_obj.history(period="1mo", interval="1h")
            
            if df.empty or len(df) < 20: continue

            k, d, j = calculate_kdj(df)
            if k is None: continue

            j_curr = j.iloc[-1]
            d_curr = d.iloc[-1]
            precio = df['Close'].iloc[-1]

            # --- SEÑALES ---
            msg = ""
            tipo = ""

            # COMPRA (Suelo: J<0 y D<25)
            if j_curr <= 0 and d_curr <= 25:
                if symbol in config.PORTFOLIO:
                    tipo = "RECOMPRA 📉"
                    msg = f"Recomendación: Promediar a la baja"
                elif config.BUSCAR_NUEVAS_ENTRADAS:
                    tipo = "NUEVA ENTRADA 💎"
                    msg = f"Oportunidad detectada"
            
            # VENTA (Techo: J>100 y D>75)
            elif j_curr >= 100 and d_curr >= 75:
                if symbol in config.PORTFOLIO:
                    tipo = "TOMA DE GANANCIAS 💰"
                    msg = f"Posible techo de mercado"

            # SI HAY SEÑAL, ENVIAR AVISO
            if msg:
                alerta = (f"🚨 **{tipo}**\n"
                          f"Ticker: {symbol} ({name})\n"
                          f"Precio: ${precio:.2f}\n"
                          f"----------------\n"
                          f"KDJ -> J:{j_curr:.1f} | D:{d_curr:.1f}\n"
                          f"💡 {msg}")
                send_telegram(alerta)
                print(f"✅ Alerta enviada: {symbol}")
                last_alerts[symbol] = time.time()
                time.sleep(1) # Pequeña pausa para no saturar si salen muchas juntas

        except Exception as e:
            continue

# ==========================================
# 🔔 TAREA SECUNDARIA: SOLO APERTURA/CIERRE
# ==========================================
def job_avisos_mercado():
    now = datetime.now(TIMEZONE)
    hora = now.strftime("%H:%M")
    if now.weekday() > 4: return

    # Solo 2 mensajes al día para saber que el bot arrancó o terminó
    if hora == "11:00":
        send_telegram("🔔 **MERCADO ABIERTO**\nIniciando vigilancia silenciosa.")
    if hora == "17:00":
        send_telegram("🔕 **MERCADO CERRADO**\nFin de la jornada.")

# ==========================================
# 🚀 MOTOR PRINCIPAL
# ==========================================
if __name__ == "__main__":
    print("🤖 BOT ACCIONES (MODO SILENCIOSO) INICIADO")
    # Mensaje de inicio (solo al reiniciar el servidor)
    send_telegram(f"🤖 **BOT ACTIVO**\nModo Silencioso: Solo alertas reales.\nHorario: 11-17hs Arg.")
    
    # 1. Escáner cada 3 MINUTOS (Pero solo avisa si encuentra algo)
    schedule.every(3).minutes.do(job_escanear_oportunidades)

    # 2. Avisos de Apertura/Cierre (Ding Dong)
    schedule.every(1).minutes.do(job_avisos_mercado)

    # Ejecutar una pasada inicial rápida por si lo prendes en medio del día
    if mercado_abierto():
        job_escanear_oportunidades()

    while True:
        schedule.run_pending()
        time.sleep(1)

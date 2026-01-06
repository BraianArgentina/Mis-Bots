# ==========================================
# 🔐 CREDENCIALES TELEGRAM (BOT WALLSTREET)
# ==========================================
# Cuando crees el bot nuevo en BotFather, pega aquí los datos.
# Mantén las comillas ""
TELEGRAM_TOKEN = "8526765460:AAEfCtglMngERcBr73-T2bDWy8JCwBhhvFE"
TELEGRAM_CHAT_ID = "-1003461057886"

# ==========================================
# 💼 MI PORTFOLIO (LO QUE YA TENGO EN COCOS)
# ==========================================
# Si el bot detecta señal aquí:
# - Si baja: Avisa RECOMPRA (Promediar).
# - Si sube: Avisa VENTA (Tomar Ganancia).
# Cuando compres algo nuevo, agrégalo a esta lista.
# Ahora con formato Diccionario para que puedas moverlas fácilmente.
PORTFOLIO = {
    'MELI': 'Mercado Libre',
    'GLOB': 'Globant',
    'META': 'Meta Platforms',
    'NFLX': 'Netflix',
    'MSTR': 'MicroStrategy',
    'JD': 'JD.com',
    'NIO': 'NIO Inc',
    'STNE': 'StoneCo',
    'TRIP': 'Tripadvisor'
}

# ==========================================
# 📋 WATCHLIST (RADAR DE OPORTUNIDADES)
# ==========================================
# Diccionario: 'TICKER_YAHOO': 'NOMBRE_MOSTRADO'
# El bot buscará NUEVAS ENTRADAS en estos activos.
WATCHLIST_DICT = {
    # --- 1. USA VOLATILIDAD / TECH ---
    'SNAP': 'SNAP', 'UBER': 'UBER', 'ZM': 'Zoom', 'ROKU': 'Roku',
    'SHOP': 'Shopify', 'ETSY': 'Etsy', 'SPOT': 'Spotify', 'SE': 'Sea Limited',
    'PLTR': 'Palantir', 'TSLA': 'Tesla', 'NVDA': 'Nvidia', 'AMD': 'AMD',
    'GOOGL': 'Google', 'SQ': 'Block', 'PYPL': 'PayPal', 'U': 'Unity',
    'DKNG': 'DraftKings', 'AFRM': 'Affirm', 'PATH': 'UiPath',
    'DDOG': 'Datadog', 'NET': 'Cloudflare', 'CRWD': 'CrowdStrike',
    'TTD': 'The Trade Desk', 'DOCU': 'DocuSign', 'QCOM': 'Qualcomm',

    # --- 2. MEME STOCKS & CRYPTO MINERS ---
    'RIOT': 'Riot Blockchain', 'MARA': 'Marathon Digital', 
    'HUT': 'Hut 8 Mining', 'CLSK': 'CleanSpark','COIN': 'Coinbase', 'BB': 'BlackBerry',
        
    # --- 3. ARGENTINA (ADRS & LOCALES) ---
    'GGAL': 'Galicia', 'PAMP': 'Pampa Energía', 'YPF': 'YPF', 
    'BMA': 'Banco Macro', 'SUPV': 'Supervielle', 'EDN': 'Edenor', 
    'CRESY': 'Cresud', 'TEO': 'Telecom', 'CEPU': 'Central Puerto', 
    'TGS': 'Gas del Sur', 'BBAR': 'BBVA Francés', 'LOMA': 'Loma Negra',
    'TX': 'Ternium', 'IRS': 'Irsa', 'DESP': 'Despegar',

    # --- 4. BRASIL, CHINA & EMERGENTES ---
    'PBR': 'Petrobras', 'VALE': 'Vale', 'NU': 'Nubank', 
    'ITUB': 'Itau Unibanco', 'BBD': 'Bradesco', 'ERJ': 'Embraer',
    'BABA': 'Alibaba', 'PDD': 'Pinduoduo', 'BIDU': 'Baidu', 
    'XPEV': 'XPeng', 'LI': 'Li Auto', 'JMIA': 'Jumia (Africa)',
    'CX': 'Cemex (México)', 'HMY': 'Harmony Gold',

    # --- 5. COMMODITIES & ENERGÍA VOLÁTIL ---
    'VIST': 'Vista Energy', 'X': 'US Steel', 
    'HAL': 'Halliburton', 'OXY': 'Occidental Petroleum', 
    'FCX': 'Freeport-McMoRan', 'AA': 'Alcoa'
}


# ==========================================
# 🛑 INTERRUPTOR DE ESTRATEGIA (MODO AHORRO)
# ==========================================
# True (Verdadero) = Busca NUEVAS oportunidades en los 70 tickers (Escenario A).
# False (Falso)    = SOLO revisa tu Portfolio para VENTA o RECOMPRA (Escenarios B y C).
BUSCAR_NUEVAS_ENTRADAS = False

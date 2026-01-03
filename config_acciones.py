# ==========================================
# 🔐 CREDENCIALES TELEGRAM (BOT WALLSTREET)
# ==========================================
# Cuando crees el bot nuevo en BotFather, pega aquí los datos.
# Mantén las comillas ""
TELEGRAM_TOKEN = "PONER_TU_TOKEN_AQUI"
TELEGRAM_CHAT_ID = "PONER_TU_CHAT_ID_AQUI"

# ==========================================
# 💼 MI PORTFOLIO (LO QUE YA TENGO EN COCOS)
# ==========================================
# Si el bot detecta señal aquí:
# - Si baja: Avisa RECOMPRA (Promediar).
# - Si sube: Avisa VENTA (Tomar Ganancia).
# Cuando compres algo nuevo, agrégalo a esta lista.
PORTFOLIO = [
    'MELI', 'GLOB', 'META', 'NFLX', 'MSTR', 'COIN', 
    'QCOM', 'HMY', 'JD', 'NIO', 'BB', 'STNE', 'TRIP'
]

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
    'TTD': 'The Trade Desk', 'DOCU': 'DocuSign',

    # --- 2. MEME STOCKS & CRYPTO MINERS ---
    'RIOT': 'Riot Blockchain', 'MARA': 'Marathon Digital', 
    'HUT': 'Hut 8 Mining', 'CLSK': 'CleanSpark',
    
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
    'CX': 'Cemex (México)',

    # --- 5. COMMODITIES & ENERGÍA VOLÁTIL ---
    'VIST': 'Vista Energy', 'X': 'US Steel', 
    'HAL': 'Halliburton', 'OXY': 'Occidental Petroleum', 
    'FCX': 'Freeport-McMoRan', 'AA': 'Alcoa'
}

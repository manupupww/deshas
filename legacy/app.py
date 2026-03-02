import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import ccxt
import os
from downloader import get_downloader

# Konfigūracija
st.set_page_config(page_title="Binance Data Dashboard", layout="wide", page_icon="🌌")

# --- MODERN UI INJECTION ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif !important;
}

/* Base App Colors */
.stApp {
    background: radial-gradient(circle at top right, #1e1b4b, #0f172a 40%, #050505 100%) !important;
    color: #f8fafc;
}

/* Sidebar Glassmorphism */
[data-testid="stSidebar"] {
    background: rgba(15, 23, 42, 0.45) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}

/* Headers */
h1, h2, h3 {
    background: linear-gradient(135deg, #e0e7ff 0%, #8b5cf6 100%);
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    font-weight: 700 !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.6rem 1.5rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3) !important;
    width: 100%;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(139, 92, 246, 0.5) !important;
}

/* Select, Date Inputs */
.stSelectbox > div > div > div, .stDateInput > div > div > div {
    background-color: rgba(30, 41, 59, 0.6) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 10px !important;
    color: white !important;
}

/* Progress bar premium styling */
.stProgress > div > div > div > div {
    background-image: linear-gradient(to right, #3b82f6, #8b5cf6) !important;
    border-radius: 10px !important;
}

/* Info Boxes */
div[data-testid="stAlert"] {
    background: rgba(30, 41, 59, 0.5) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.5);
    backdrop-filter: blur(10px);
}
</style>
""", unsafe_allow_html=True)

# Inicializuojame Binance klientą per CCXT
@st.cache_resource

def get_binance_client():
    return ccxt.binance()

binance = get_binance_client()
downloader = get_downloader()

# --- ŠONINĖ JUOSTA (Sidebar) ---
st.sidebar.title("⚙️ Konfigūracija")

# 1. Simbolio pasirinkimas
@st.cache_data(ttl=3600)
def get_all_symbols():
    markets = binance.load_markets()
    return sorted(list(markets.keys()))

symbols = get_all_symbols()
selected_symbol = st.sidebar.selectbox("Pasirinkite simbolį", symbols, index=symbols.index('BTC/USDT') if 'BTC/USDT' in symbols else 0)

# 2. Timeframe pasirinkimas
intervals = ['1s', '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1mo']
selected_interval = st.sidebar.selectbox("Pasirinkite intervalą (Timeframe)", intervals, index=intervals.index('1m'))

# 3. Duomenų tipas
data_types = ['Klines (OHLCV)', 'Liquidations', 'AggTrades', 'Dollar Bars (ML Ready)', 'Time-Series Aggregator (Cloud)']
selected_data_type = st.sidebar.radio("Duomenų tipas", data_types)

# 4. Dollar Bars Slenkstis (jei pasirinkta)
dollar_threshold = 1_000_000
if selected_data_type == 'Dollar Bars (ML Ready)':
    dollar_threshold = st.sidebar.number_input("Dollar Threshold ($)", value=1_000_000, step=100_000)

# 5. Laiko rėmiai
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("Pradžia", datetime.now() - timedelta(days=7))
with col2:
    end_date = st.date_input("Pabaiga", datetime.now())

# 5. Papildomi nustatymai
save_locally = st.sidebar.checkbox("Išsaugoti lokaliai (data/ aplanke)", value=True)

# --- PAGRINDINIS LANGAI (Main Area) ---
st.title(f"📊 Binance {selected_data_type} Dashboard")
st.info(f"Pasirinkta: **{selected_symbol}** | Intervalas: **{selected_interval}** | Laikotarpis: {start_date} iki {end_date}")

# Mygtukas atsisiuntimui
if st.button("🚀 Vykdyti"):
    loader_placeholder = st.empty()
    loader_placeholder.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px; background: rgba(30,41,59,0.5); border-radius: 20px; border: 1px solid rgba(255,255,255,0.05); backdrop-filter: blur(15px); margin: 30px 0; box-shadow: 0 10px 40px rgba(0,0,0,0.3);">
            <div class="loader-neon"></div>
            <h3 style="margin-top: 30px; margin-bottom: 5px; font-family: 'Outfit', sans-serif; font-weight: 600; font-size: 1.5rem; letter-spacing: 0.5px; background: linear-gradient(135deg, #e0e7ff 0%, #8b5cf6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Kraunami duomenys...</h3>
            <p style="color: #94a3b8; font-size: 1rem; margin: 0;">Apdorojama: <b>{selected_data_type}</b></p>
        </div>
        <style>
        .loader-neon {{
          width: 70px;
          height: 70px;
          border-radius: 50%;
          border: 4px solid transparent;
          border-top-color: #3b82f6;
          border-bottom-color: #8b5cf6;
          animation: spin-pulse 1.2s cubic-bezier(0.5, 0.1, 0.4, 0.9) infinite;
          box-shadow: 0 0 25px rgba(59, 130, 246, 0.5), inset 0 0 25px rgba(139, 92, 246, 0.5);
        }}
        @keyframes spin-pulse {{
          0% {{ transform: rotate(0deg) scale(1); }}
          50% {{ transform: rotate(180deg) scale(1.1); }}
          100% {{ transform: rotate(360deg) scale(1); }}
        }}
        </style>
    """, unsafe_allow_html=True)
    
    progress_bar = st.progress(0)
    
    try:
        data = pd.DataFrame()
        
        if selected_data_type == 'Klines (OHLCV)':
            data = downloader.fetch_klines(
                selected_symbol, 
                selected_interval, 
                start_date.isoformat(), 
                end_date.isoformat(),
                progress_callback=lambda p: progress_bar.progress(p)
            )
        
        elif selected_data_type == 'Liquidations':
            data = downloader.fetch_vision_data(
                'liquidationOrders',
                selected_symbol,
                start_date.isoformat(),
                end_date.isoformat(),
                progress_callback=lambda p: progress_bar.progress(p)
            )

        elif selected_data_type == 'AggTrades':
            data = downloader.fetch_vision_data(
                'aggTrades',
                selected_symbol,
                start_date.isoformat(),
                end_date.isoformat(),
                progress_callback=lambda p: progress_bar.progress(p)
            )

        elif selected_data_type == 'Dollar Bars (ML Ready)':
            st.write("⏳ Siunčiami AggTrades ir generuojami Dollar Bars...")
            agg_trades = downloader.fetch_vision_data(
                'aggTrades',
                selected_symbol,
                start_date.isoformat(),
                end_date.isoformat(),
                progress_callback=lambda p: progress_bar.progress(p * 0.8) # 80% siuntimui
            )
            if not agg_trades.empty:
                st.write("⚙️ Konvertuojama į Dollar Bars...")
                data = downloader.create_dollar_bars(agg_trades, threshold=dollar_threshold)
                progress_bar.progress(1.0)
            else:
                data = pd.DataFrame()

        elif selected_data_type == 'Time-Series Aggregator (Cloud)':
            loader_placeholder.empty()
            st.write("### 🌩️ Modal Cloud Data Processing")
            st.info("Ši funkcija leidžia apdoroti milžiniškus duomenų kiekius (pvz. 1 metus AggTrades) per kelias minutes naudojant Modal debesį.")
            
            agg_mode = st.radio("Pasirinkite agregavimo tipą", ["Standard (Klines + Liq)", "Dollar Bars"])
            
            if st.button("🚀 Paleisti debesyje (Modal)"):
                with st.spinner("Siunčiama užklausa į Modal..."):
                    cmd_tf = selected_interval if agg_mode == "Standard (Klines + Liq)" else "Dollar Bars"
                    # Čia galime pridėti tiesioginį iškvietimą per modal biblioteką ateityje, 
                    # dabar rodome komandą, kurią vartotojas gali paleisti arba mes galime paleisti per subprocess.
                    cmd = f"modal run dashboard/modal_worker.py --symbol {selected_symbol.replace('/', '')} --timeframe \"{cmd_tf}\" --start {start_date} --end {end_date}"
                    st.code(cmd, language="bash")
                    st.warning("Užklausa užregistruota. Rezultatą rasite savo Modal paskyroje arba stebėkite terminalą.")
            progress_bar.progress(1.0)
            st.stop()

        loader_placeholder.empty()

        if not data.empty:
            st.success(f"✅ Apdorojimas baigtas! Iš viso: {len(data)} eilučių.")
            st.subheader("Duomenų peržiūra")
            st.dataframe(data.tail(100))

            csv_name = f"{selected_symbol.replace('/', '_')}_{selected_interval}_{selected_data_type.split()[0]}.csv"
            csv = data.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="💾 Atsisiųsti CSV failą",
                data=csv,
                file_name=csv_name,
                mime='text/csv',
            )

            if save_locally:
                filepath = downloader.save_to_csv(
                    data, 
                    selected_symbol, 
                    selected_data_type.split()[0], 
                    selected_interval
                )
                if filepath:
                    st.success(f"📂 Failas išsaugotas: `{filepath}`")
        else:
            st.warning("⚠️ Duomenų nerasta.")
            
    except Exception as e:
        loader_placeholder.empty()
        st.error(f"❌ Klaida: {str(e)}")
    
    progress_bar.progress(1.0)

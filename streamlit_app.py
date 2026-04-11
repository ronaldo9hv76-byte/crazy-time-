import streamlit as st
import os
import time

# --- FIX DIPENDENZE CLOUD ---
# Eseguiamo l'installazione dei binari all'avvio dell'app per bypassare l'OS
@st.cache_resource
def install_playwright_binaries():
    with st.spinner("Configurazione ambiente browser... Attendere."):
        # Installazione isolata di Chromium e delle sue librerie minime
        os.system("playwright install chromium")
        os.system("playwright install-deps chromium")

install_playwright_binaries()

# Importazioni post-setup
import numpy as np
import pandas as pd
from collections import Counter
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

# --- LOGICA MATEMATICA ---
SEGMENTS = ['1', '2', '5', '10', 'Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
THEORETICAL_PROBS = {
    '1': 21/54, '2': 13/54, '5': 7/54, '10': 4/54, 
    'Coin Flip': 4/54, 'Pachinko': 2/54, 'Cash Hunt': 2/54, 'Crazy Time': 1/54
}

def get_markov_matrix(history):
    """Crea la matrice di transizione per pattern sequenziali."""
    matrix = pd.DataFrame(0.1, index=SEGMENTS, columns=SEGMENTS)
    for i in range(len(history) - 1):
        curr, nxt = history[i], history[i+1]
        if curr in SEGMENTS and nxt in SEGMENTS:
            matrix.loc[curr, nxt] += 1
    return matrix.div(matrix.sum(axis=1), axis=0)

def calculate_stats(history):
    """Analisi Z-Score ed Entropia."""
    n = len(history)
    counts = Counter(history)
    z_scores = {
        s: (counts[s] - n*THEORETICAL_PROBS[s]) / np.sqrt(n*THEORETICAL_PROBS[s]*(1-THEORETICAL_PROBS[s])) 
        if n > 0 else 0 for s in SEGMENTS
    }
    probs = [counts.get(s, 0)/n if n > 0 else 0 for s in SEGMENTS]
    entropy = -sum(p * np.log2(p) for p in probs if p > 0)
    return z_scores, entropy

# --- INTERFACCIA UTENTE (UI) ---
st.set_page_config(page_title="Crazy Math Pro", layout="wide", page_icon="📈")
st.title("📊 Crazy Time: Markov & Bias Predictor")

if "history" not in st.session_state:
    st.session_state.history = []

# Sidebar
st.sidebar.header("⚙️ Impostazioni")
target_url = st.sidebar.text_input("URL Sorgente Dati", "https://www.trackcasinos.com/crazy-time-stats/")
refresh_time = st.sidebar.slider("Intervallo Aggiornamento (s)", 30, 120, 60)
run_app = st.sidebar.button("▶️ Avvia Analisi", type="primary")

if run_app:
    ui_container = st.empty()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # User Agent specifico per iPhone per evitare ban
        context = browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()
        stealth_sync(page)

        while True:
            try:
                page.goto(target_url, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(4000) # Buffer per caricamento dati live
                
                # Scraping testuale resiliente
                raw_text = page.query_selector_all("td, span, div.result")
                history = [el.inner_text().strip() for el in raw_text if el.inner_text().strip() in SEGMENTS][:100]
                
                if history:
                    st.session_state.history = history
                    z_scores, entropy = calculate_stats(history)
                    matrix = get_markov_matrix(history)
                    last_val = history[0]
                    
                    # Calcolo Probabilità Ibrida (70% Markov + 30% Bias Statistico)
                    m_weights = matrix.loc[last_val].values
                    b_weights = np.array([max(0.01, THEORETICAL_PROBS[s] + z_scores[s]*0.02) for s in SEGMENTS])
                    final_weights = (m_weights * 0.7) + (b_weights * 0.3)
                    final_weights /= final_weights.sum()
                    
                    predictions = np.random.choice(SEGMENTS, size=30, p=final_weights)

                    with ui_container.container():
                        # Dashboard Metriche
                        col_a, col_b, col_c = st.columns(3)
                        col_a.metric("Ultima Estrazione", last_val)
                        col_b.metric("Entropia (Incertezza)", f"{entropy:.3f}")
                        col_c.metric("Pattern Status", "STABILE" if entropy < 2.3 else "CAOTICO")

                        st.divider()
                        st.subheader("🎯 Previsione Prossime 30 Giocate")
                        st.success(" → ".join([f"**{p}**" for p in predictions]))

                        # Dettagli Tecnici
                        col_left, col_right = st.columns([2, 1])
                        with col_left:
                            st.write("**Probabilità Condizionate (Matrice di Markov)**")
                            st.dataframe(matrix.style.background_gradient(axis=1, cmap='Blues'), use_container_width=True)
                        with col_right:
                            st.write("**Anomalie (Z-Score)**")
                            df_z = pd.DataFrame(z_scores.items(), columns=['Esito', 'Z']).set_index('Esito')
                            st.dataframe(df_z.style.background_gradient(cmap='RdYlGn', vmin=-2, vmax=2), use_container_width=True)
                        
                        st.caption(f"Ultimo Check: {time.strftime('%H:%M:%S')} | Campione: {len(history)} giri")

                time.sleep(refresh_time)
                page.reload()
                
            except Exception as e:
                st.sidebar.warning(f"Riconnessione in corso... ({e})")
                time.sleep(10)

import streamlit as st
import numpy as np
import pandas as pd
import time
from collections import Counter
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

# --- SETUP MATEMATICO ---
SEGMENTS = ['1', '2', '5', '10', 'Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
THEORETICAL_PROBS = {'1': 21/54, '2': 13/54, '5': 7/54, '10': 4/54, 'Coin Flip': 4/54, 'Pachinko': 2/54, 'Cash Hunt': 2/54, 'Crazy Time': 1/54}

def get_markov_matrix(history):
    """Crea una matrice di transizione basata sulle sequenze osservate."""
    matrix = pd.DataFrame(0.1, index=SEGMENTS, columns=SEGMENTS) # Inizializzazione con smoothing
    for i in range(len(history) - 1):
        curr, nxt = history[i], history[i+1]
        if curr in SEGMENTS and nxt in SEGMENTS:
            matrix.loc[curr, nxt] += 1
    return matrix.div(matrix.sum(axis=1), axis=0)

def calculate_stats(history):
    n = len(history)
    counts = Counter(history)
    z_scores = {s: (counts[s] - n*THEORETICAL_PROBS[s]) / np.sqrt(n*THEORETICAL_PROBS[s]*(1-THEORETICAL_PROBS[s])) if n > 0 else 0 for s in SEGMENTS}
    probs = [counts.get(s, 0)/n if n > 0 else 0 for s in SEGMENTS]
    entropy = -sum(p * np.log2(p) for p in probs if p > 0)
    return z_scores, entropy

# --- UI STREAMLIT ---
st.set_page_config(page_title="Crazy Math Pro", layout="wide", page_icon="📈")
st.title("📈 Crazy Time Markovian Predictor")

if "history" not in st.session_state:
    st.session_state.history = []

url = st.sidebar.text_input("URL Stats", "https://www.casino.org/crazy-time/stats/")
run = st.sidebar.button("Avvia Monitoraggio")

if run:
    placeholder = st.empty()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
        page = context.new_page()
        stealth_sync(page) # Evita i blocchi bot

        while True:
            try:
                page.goto(url, wait_until="networkidle")
                page.wait_for_timeout(2000)
                
                # Scraping dei dati (metodo smart text-based)
                raw_elements = page.query_selector_all("td, span, div")
                new_h = [el.inner_text().strip() for el in raw_elements if el.inner_text().strip() in SEGMENTS][:100]
                
                if new_h:
                    st.session_state.history = new_h
                    z_scores, entropy = calculate_stats(new_h)
                    matrix = get_markov_matrix(new_h)
                    last_result = new_h[0]
                    
                    # Predizione basata sull'ultimo risultato (Markov) + Bias (Z-Score)
                    markov_weights = matrix.loc[last_result].values
                    bias_weights = np.array([max(0.01, THEORETICAL_PROBS[s] + z_scores[s]*0.02) for s in SEGMENTS])
                    combined_weights = (markov_weights * 0.7) + (bias_weights * 0.3)
                    combined_weights /= combined_weights.sum()
                    
                    preds = np.random.choice(SEGMENTS, size=30, p=combined_weights)

                    with placeholder.container():
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Ultimo Uscito", last_result)
                        m2.metric("Entropia", f"{entropy:.3f}", delta=f"{entropy - 2.45:.3f}", delta_color="inverse")
                        m3.metric("Affidabilità Markov", "Alta" if entropy < 2.3 else "Bassa")

                        st.subheader("🎯 Prossime 30 Giocate (Markov-Bias Hybrid)")
                        st.info(" ➔ ".join(preds))

                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.write("**Matrice di Transizione (Probabilità Sequenziali)**")
                            st.dataframe(matrix.style.background_gradient(axis=1))
                        with c2:
                            st.write("**Deviazioni Standard (Z-Score)**")
                            st.dataframe(pd.DataFrame(z_scores.items(), columns=['S', 'Z']).set_index('S').style.background_gradient(cmap='RdYlGn'))
                
                time.sleep(60)
                page.reload()
            except Exception as e:
                st.error(f"Errore connessione: {e}")
                time.sleep(10)

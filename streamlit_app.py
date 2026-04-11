import streamlit as st
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from collections import Counter

# --- CONFIGURAZIONE ---
SEGMENTS = ['1', '2', '5', '10', 'Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
THEORETICAL_PROBS = {'1': 21/54, '2': 13/54, '5': 7/54, '10': 4/54, 'Coin Flip': 4/54, 'Pachinko': 2/54, 'Cash Hunt': 2/54, 'Crazy Time': 1/54}

def get_markov_matrix(history):
    matrix = pd.DataFrame(0.1, index=SEGMENTS, columns=SEGMENTS)
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

def fetch_data(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    }
    try:
        # Tentativo di recupero
        response = requests.get(url, headers=headers, timeout=15)
        
        # Se riceviamo 403, comunichiamo il blocco
        if response.status_code == 403:
            return "Errore 403: Il sito blocca l'accesso automatico. Prova a usare l'URL di Tracksino o simili."
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # Cerchiamo i nomi dei segmenti in span o div con classi comuni
        tags = soup.find_all(['span', 'div', 'p'])
        history = [t.get_text().strip() for t in tags if t.get_text().strip() in SEGMENTS]
        
        # Pulizia duplicati tecnici
        clean_h = []
        for i, val in enumerate(history):
            if i == 0 or val != history[i-1]:
                clean_h.append(val)
        return clean_h[:100]
    except Exception as e:
        return f"Errore: {str(e)}"

# --- UI ---
st.set_page_config(page_title="Crazy Math Mobile", layout="wide")
st.title("🎡 Crazy Time Tracker")

st.sidebar.header("Impostazioni")
# Cambiamo l'URL di default con uno potenzialmente meno protetto o suggeriamo l'alternativa
url_input = st.sidebar.text_input("URL Statistiche", "https://www.trackcasinos.com/crazy-time-stats/")
run = st.sidebar.toggle("Avvia Analisi")

if run:
    container = st.empty()
    while run:
        history = fetch_data(url_input)
        
        if isinstance(history, list) and len(history) > 5:
            z_scores, entropy = calculate_stats(history)
            matrix = get_markov_matrix(history)
            last = history[0]
            
            # Predizione
            m_w = matrix.loc[last].values
            b_w = np.array([max(0.01, THEORETICAL_PROBS[s] + z_scores[s]*0.02) for s in SEGMENTS])
            final_w = (m_w * 0.7) + (b_w * 0.3)
            final_w /= final_w.sum()
            preds = np.random.choice(SEGMENTS, size=15, p=final_w)

            with container.container():
                st.metric("Ultimo Esito", last, f"Entropia: {entropy:.2f}")
                st.success("➔ ".join(preds))
                st.write("**Matrice di Probabilità Condizionata**")
                st.dataframe(matrix.style.background_gradient(axis=1, cmap='Blues'))
                st.caption(f"Aggiornato: {time.strftime('%H:%M:%S')}")
        else:
            st.error(f"Impossibile leggere i dati: {history}")
            st.info("Suggerimento: Il sito inserito potrebbe avere protezioni anti-bot. Prova a cercare un sito di stats 'Crazy Time Live' meno noto o più semplice.")
            break
        time.sleep(45)

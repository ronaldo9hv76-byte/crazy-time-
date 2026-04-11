import streamlit as st
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from collections import Counter

# --- CONFIGURAZIONE MATEMATICA ---
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
    # Header Safari iPhone avanzato
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9"
    }
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            return f"Errore Server: {response.status_code}"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Cerchiamo i dati in modo più ampio: span, div, td che contengono i nomi dei bonus
        elements = soup.find_all(['span', 'div', 'td'])
        history = []
        for el in elements:
            txt = el.get_text().strip()
            if txt in SEGMENTS:
                history.append(txt)
        
        # Rimuoviamo i duplicati consecutivi dovuti a sovrapposizioni HTML
        clean_history = []
        for i in range(len(history)):
            if i == 0 or history[i] != history[i-1]:
                clean_history.append(history[i])
                
        return clean_history[:100]
    except Exception as e:
        return f"Errore Connessione: {str(e)}"

# --- INTERFACCIA ---
st.set_page_config(page_title="Crazy Math Safari", layout="wide")
st.title("🎡 Crazy Time: Analisi Matematica")

# Sidebar con istruzioni
st.sidebar.header("⚙️ Pannello Controllo")
default_url = "https://www.casino.org/casinoscores/it/crazy-time/"
url = st.sidebar.text_input("Inserisci URL Statistiche", default_url)
run = st.sidebar.toggle("▶️ ATTIVA MONITORAGGIO") # Usiamo un toggle più stabile per Safari

if run:
    status_box = st.empty()
    display_box = st.empty()
    
    while run:
        status_box.write("⏳ Recupero dati in corso...")
        history = fetch_data(url)
        
        if isinstance(history, list) and len(history) > 2:
            z_scores, entropy = calculate_stats(history)
            matrix = get_markov_matrix(history)
            last = history[0]
            
            # Predizione Markov + Bias
            m_weights = matrix.loc[last].values
            b_weights = np.array([max(0.01, THEORETICAL_PROBS[s] + z_scores[s]*0.02) for s in SEGMENTS])
            weights = (m_weights * 0.7) + (b_weights * 0.3)
            weights /= weights.sum()
            preds = np.random.choice(SEGMENTS, size=20, p=weights)

            with display_box.container():
                st.success(f"Dati letti correttamente! ({len(history)} giri analizzati)")
                
                m1, m2 = st.columns(2)
                m1.metric("Ultimo Esito", last)
                m2.metric("Entropia", f"{entropy:.2f}")

                st.info("🎯 **PREVISIONE PROSSIMI GIRI:**\n\n" + " ➔ ".join([f"**{p}**" for p in preds]))
                
                with st.expander("Vedi Matrice di Probabilità"):
                    st.dataframe(matrix.style.background_gradient(axis=1, cmap='Purples'))
                    
                st.caption(f"Ultimo aggiornamento: {time.strftime('%H:%M:%S')}")
                status_box.empty()
        else:
            status_box.error(f"⚠️ Attenzione: {history if isinstance(history, str) else 'Dati non trovati nella pagina. Prova a cambiare URL o attendi.'}")
            
        time.sleep(30) # Refresh ogni 30 secondi per essere più reattivi
else:
    st.write("Configura l'URL e attiva il monitoraggio dalla barra laterale per iniziare.")

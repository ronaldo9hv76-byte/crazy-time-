import streamlit as st
import numpy as np
import pandas as pd
import time
from collections import Counter
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

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

# --- SETUP BROWSER (SELENIUM) ---
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1")
    return webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()), options=options)

# --- UI ---
st.set_page_config(page_title="Crazy Math Pro", layout="wide")
st.title("📊 Crazy Time Markovian Predictor")

if "history" not in st.session_state:
    st.session_state.history = []

url = st.sidebar.text_input("URL Stats", "https://www.casino.org/crazy-time/stats/")
run = st.sidebar.button("▶️ Avvia Monitoraggio", type="primary")

if run:
    placeholder = st.empty()
    driver = get_driver()
    
    while True:
        try:
            driver.get(url)
            time.sleep(5)
            # Estrazione dati
            elements = driver.find_elements("xpath", "//*[self::td or self::span or self::div]")
            history = [el.text.strip() for el in elements if el.text.strip() in SEGMENTS][:100]
            
            if history:
                z_scores, entropy = calculate_stats(history)
                matrix = get_markov_matrix(history)
                last = history[0]
                
                # Predizione ibrida
                m_weights = matrix.loc[last].values
                b_weights = np.array([max(0.01, THEORETICAL_PROBS[s] + z_scores[s]*0.02) for s in SEGMENTS])
                weights = (m_weights * 0.7) + (b_weights * 0.3)
                weights /= weights.sum()
                preds = np.random.choice(SEGMENTS, size=30, p=weights)

                with placeholder.container():
                    st.metric("Ultimo Uscito", last, delta=f"H: {entropy:.2f}")
                    st.success("➔ ".join(preds))
                    
                    c1, c2 = st.columns([2, 1])
                    c1.dataframe(matrix.style.background_gradient(axis=1))
                    df_z = pd.DataFrame(z_scores.items(), columns=['S', 'Z']).set_index('S')
                    c2.dataframe(df_z.style.background_gradient(cmap='RdYlGn'))
            
            time.sleep(60)
        except Exception as e:
            st.error(f"Errore: {e}")
            break
    driver.quit()

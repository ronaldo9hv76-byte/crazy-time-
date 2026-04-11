import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter

# Configurazione fissa
SEGMENTS = ['1', '2', '5', '10', 'Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
THEORETICAL = {'1': 21/54, '2': 13/54, '5': 7/54, '10': 4/54, 'Coin Flip': 4/54, 'Pachinko': 2/54, 'Cash Hunt': 2/54, 'Crazy Time': 1/54}

st.set_page_config(page_title="CrazyPro", layout="wide")

# Inizializzazione Sessione (Fondamentale per iPhone)
if 'history' not in st.session_state:
    st.session_state['history'] = []

st.title("🎲 Crazy Time Tracker")

# --- AREA PULSANTI ---
st.write(f"### Giri registrati: {len(st.session_state.history)}")

# Layout a griglia per dita grandi
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("1", use_container_width=True): st.session_state.history.insert(0, '1')
    if st.button("COIN", use_container_width=True): st.session_state.history.insert(0, 'Coin Flip')
with c2:
    if st.button("2", use_container_width=True): st.session_state.history.insert(0, '2')
    if st.button("PACH", use_container_width=True): st.session_state.history.insert(0, 'Pachinko')
with c3:
    if st.button("5", use_container_width=True): st.session_state.history.insert(0, '5')
    if st.button("CASH", use_container_width=True): st.session_state.history.insert(0, 'Cash Hunt')
with c4:
    if st.button("10", use_container_width=True): st.session_state.history.insert(0, '10')
    if st.button("CRAZY", use_container_width=True): st.session_state.history.insert(0, 'Crazy Time')

st.divider()

# --- LOGICA MATEMATICA ---
if len(st.session_state.history) > 1:
    h = st.session_state.history
    last = h[0]
    
    # Calcolo Z-Score
    n = len(h)
    counts = Counter(h)
    z_data = {}
    for s in SEGMENTS:
        p = THEORETICAL[s]
        exp = n * p
        sd = np.sqrt(n * p * (1-p))
        z_data[s] = (counts.get(s, 0) - exp) / sd if sd > 0 else 0
    
    # Calcolo Markov semplice (senza gradienti che danno errore)
    matrix = pd.DataFrame(0.0, index=SEGMENTS, columns=SEGMENTS)
    h_rev = h[::-1]
    for i in range(len(h_rev)-1):
        matrix.loc[h_rev[i], h_rev[i+1]] += 1
    
    # UI DI ANALISI
    st.subheader(f"Ultimo: {last}")
    
    # Suggerimento testuale (Zero Grafica = Zero Errori)
    row = matrix.loc[last]
    if row.sum() > 0:
        sugg = row.idxmax()
        st.success(f"🎯 Probabilità statistica: **{sugg}**")
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.write("**Frequenze Recenti**")
        st.table(pd.Series(counts).head(8)) # Usiamo st.table che è più stabile di st.dataframe
    with col_right:
        st.write("**Z-Score (Bias)**")
        st.table(pd.Series(z_data).round(2))

    if st.button("🗑️ Reset Dati"):
        st.session_state.history = []
        st.rerun()
else:
    st.info("Inserisci almeno 2 dati per vedere l'analisi.")

import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter

# --- COSTANTI MATEMATICHE ---
SEGMENTS = ['1', '2', '5', '10', 'Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
THEORETICAL_PROBS = {
    '1': 21/54, '2': 13/54, '5': 7/54, '10': 4/54, 
    'Coin Flip': 4/54, 'Pachinko': 2/54, 'Cash Hunt': 2/54, 'Crazy Time': 1/54
}
EXPECTED_ENTROPY = 2.45

# --- MOTORE INFERENZIALE ---

# 1. Entropia di Shannon
def calculate_entropy(history):
    if not history: return 0.0
    counts = Counter(history)
    probs = [counts.get(s, 0) / len(history) for s in SEGMENTS]
    return -sum(p * np.log2(p) for p in probs if p > 0)

# 2. Analisi Z-Score
def calculate_z_scores(history):
    n = len(history)
    counts = Counter(history)
    z_scores = {}
    for s in SEGMENTS:
        p = THEORETICAL_PROBS[s]
        expected = n * p
        std_dev = np.sqrt(n * p * (1 - p))
        z_scores[s] = (counts.get(s, 0) - expected) / std_dev if std_dev > 0 else 0
    return z_scores

# 3. Matrice di Markov (Probabilità Condizionata con Laplace Smoothing)
def get_markov_matrix(history, alpha=0.1):
    matrix = pd.DataFrame(alpha, index=SEGMENTS, columns=SEGMENTS)
    if len(history) < 2: return matrix.div(matrix.sum(axis=1), axis=0)
    
    # Riordino cronologico per le transizioni corrette (da meno recente a più recente)
    chronological = list(reversed(history))
    for i in range(len(chronological) - 1):
        prev, curr = chronological[i], chronological[i+1]
        if prev in SEGMENTS and curr in SEGMENTS:
            matrix.loc[prev, curr] += 1
            
    return matrix.div(matrix.sum(axis=1), axis=0)

# 4. Test di Wald-Wolfowitz (Runs Test per la casualità)
def wald_wolfowitz_test(history):
    if len(history) < 5: return 0, "Dati Insufficienti"
    
    chronological = list(reversed(history))
    # Binario: 0 per Numeri base, 1 per Bonus
    binary = [1 if s in ['Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time'] else 0 for s in chronological]
    
    n1 = sum(binary) # Totale Bonus
    n2 = len(binary) - n1 # Totale Numeri
    if n1 == 0 or n2 == 0: return 0, "Serie Monotona"
    
    runs = 1
    for i in range(1, len(binary)):
        if binary[i] != binary[i-1]:
            runs += 1
            
    expected_runs = ((2 * n1 * n2) / (n1 + n2)) + 1
    variance = (2 * n1 * n2 * (2 * n1 * n2 - n1 - n2)) / (((n1 + n2) ** 2) * (n1 + n2 - 1)) if (n1+n2)>1 else 1
    z_runs = (runs - expected_runs) / np.sqrt(variance) if variance > 0 else 0
    
    if z_runs < -1.96: status = "Tendenza ai Cluster (Rigido)"
    elif z_runs > 1.96: status = "Alternanza Eccessiva (Caotico)"
    else: status = "Casuale (Naturale)"
    
    return z_runs, status

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Crazy Math Pro", layout="wide", page_icon="🎲")

if "history" not in st.session_state:
    st.session_state.history = []

st.title("🎲 Crazy Time: Advanced Manual Tracker")

# Tastierino Mobile
st.subheader("Inserimento Rapido")
cols = st.columns(4)
btn_labels = SEGMENTS[:4] + ['CF', 'PACH', 'CASH', 'CRAZY']
for i, (s, label) in enumerate(zip(SEGMENTS, btn_labels)):
    if cols[i % 4].button(label, use_container_width=True):
        st.session_state.history.insert(0, s)

col_annulla, col_reset = st.columns(2)
if col_annulla.button("↩️ Annulla Ultimo", use_container_width=True):
    if st.session_state.history:
        st.session_state.history.pop(0)
if col_reset.button("🗑️ Azzera Dati", use_container_width=True, type="primary"):
    st.session_state.history = []
    st.rerun()

st.divider()

# Esecuzione Matematica
if st.session_state.history:
    history = st.session_state.history[:100]
    last = history[0]
    
    # Calcoli
    z_scores = calculate_z_scores(history)
    matrix = get_markov_matrix(history)
    h_long = calculate_entropy(history)
    h_short = calculate_entropy(history[:20])
    z_runs, ww_status = wald_wolfowitz_test(history)
    
    # Vettore Predittivo Ibrido
    m_weights = matrix.loc[last].values
    b_weights = np.array([max(0.01, THEORETICAL_PROBS[s] + z_scores[s]*0.02) for s in SEGMENTS])
    weights = (m_weights * 0.7) + (b_weights * 0.3)
    weights /= weights.sum()
    preds = np.random.choice(SEGMENTS, size=15, p=weights)

    # Output Metriche
    st.success("🎯 **PREVISIONE: " + " ➔ ".join([f"{p}" for p in preds]) + "**")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Giri Registrati", len(history))
    c2.metric("Entropia L/T", f"{h_long:.2f}")
    c3.metric("Entropia B/T (Drift)", f"{h_short:.2f}", delta=f"{h_short - h_long:.2f}", delta_color="inverse")
    
    st.info(f"🧬 **Test Sequenziale di Wald-Wolfowitz:** {ww_status} (Z-Score: {z_runs:.2f})")

    # Tabelle Dati
    with st.expander("📊 Apri Matrice di Markov & Z-Scores", expanded=True):
        col_m, col_z = st.columns([2, 1])
        with col_m:
            st.write("Catena di Transizione")
            st.dataframe(matrix.style.background_gradient(axis=1, cmap='Purples'), use_container_width=True)
        with col_z:
            st.write("Bias (Z-Score)")
            df_z = pd.DataFrame(z_scores.items(), columns=['Segmento', 'Z']).set_index('Segmento')
            st.dataframe(df_z.style.background_gradient(cmap='RdYlGn', vmin=-2, vmax=2), use_container_width=True)
else:
    st.info("👈 Inserisci il primo risultato dal tastierino per inizializzare il motore matematico.")

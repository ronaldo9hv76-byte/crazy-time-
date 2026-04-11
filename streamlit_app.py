import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter

# --- SETUP INIZIALE E COSTANTI ---
st.set_page_config(page_title="Crazy Math Pro", page_icon="🎲", layout="wide")

SEGMENTS = ['1', '2', '5', '10', 'Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
THEORETICAL_PROBS = {
    '1': 21/54, '2': 13/54, '5': 7/54, '10': 4/54, 
    'Coin Flip': 4/54, 'Pachinko': 2/54, 'Cash Hunt': 2/54, 'Crazy Time': 1/54
}

# Gestione sicura della memoria su iPhone
if 'history' not in st.session_state:
    st.session_state['history'] = []

# --- MOTORE MATEMATICO ---
def calculate_metrics(history):
    n = len(history)
    counts = Counter(history)
    
    # 1. Z-Score (Deviazioni dalla media standardizzata)
    z_scores = {}
    for s in SEGMENTS:
        p = THEORETICAL_PROBS[s]
        expected = n * p
        variance = n * p * (1 - p)
        std_dev = np.sqrt(variance)
        z_scores[s] = (counts.get(s, 0) - expected) / std_dev if std_dev > 0 else 0
        
    # 2. Entropia di Shannon (Misura del caos)
    def calc_entropy(data):
        if not data: return 0.0
        c = Counter(data)
        probs = [c.get(s, 0) / len(data) for s in SEGMENTS]
        return -sum(p * np.log2(p) for p in probs if p > 0)
    
    h_total = calc_entropy(history)
    h_recent = calc_entropy(history[:20]) # Ultime 20 giocate per il drift (Sliding Window)
    
    # 3. Test di Wald-Wolfowitz (Analisi Cluster: Numeri vs Bonus)
    binary = [1 if x in ['Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time'] else 0 for x in history]
    runs = 1
    for i in range(1, len(binary)):
        if binary[i] != binary[i-1]: runs += 1
        
    n1 = sum(binary) # Quantità di Bonus
    n2 = n - n1      # Quantità di Numeri Base
    
    ww_status = "In calcolo..."
    if n1 > 0 and n2 > 0 and n > 2:
        exp_runs = ((2 * n1 * n2) / n) + 1
        var_runs = (2 * n1 * n2 * (2 * n1 * n2 - n)) / ((n**2) * (n - 1))
        if var_runs > 0:
            ww_z = (runs - exp_runs) / np.sqrt(var_runs)
            if ww_z < -1.96: ww_status = "Cluster (Trend Ripetitivo)"
            elif ww_z > 1.96: ww_status = "Alternanza (Troppo Regolare)"
            else: ww_status = "Casuale (Naturale)"

    # 4. Catene di Markov (Matrice di Transizione)
    matrix = pd.DataFrame(0.0, index=SEGMENTS, columns=SEGMENTS)
    h_rev = history[::-1] # Dal più vecchio al più recente per tracciare il tempo
    for i in range(len(h_rev)-1):
        matrix.loc[h_rev[i], h_rev[i+1]] += 1
        
    # Normalizzazione per riga (Probabilità condizionata)
    row_sums = matrix.sum(axis=1).replace(0, 1)
    matrix_norm = matrix.div(row_sums, axis=0)
    
    return z_scores, h_total, h_recent, runs, ww_status, matrix_norm

# --- INTERFACCIA UTENTE (UI) ---
st.title("🧮 Crazy Time Pro Tracker")

# Tastierino input (Ottimizzato per dita su Safari Mobile)
st.write(f"**Giri Analizzati:** {len(st.session_state.history)}")
c1, c2, c3, c4 = st.columns(4)
buttons = [
    ("1", "1", c1), ("2", "2", c2), ("5", "5", c3), ("10", "10", c4),
    ("COIN", "Coin Flip", c1), ("PACH", "Pachinko", c2), ("CASH", "Cash Hunt", c3), ("CRAZY", "Crazy Time", c4)
]

for label, value, col in buttons:
    if col.button(label, use_container_width=True):
        st.session_state.history.insert(0, value)
        st.rerun()

col_undo, col_reset = st.columns(2)
if col_undo.button("↩️ Annulla Ultimo", use_container_width=True):
    if st.session_state.history:
        st.session_state.history.pop(0)
        st.rerun()
if col_reset.button("🗑️ Reset Totale", use_container_width=True, type="primary"):
    st.session_state.history = []
    st.rerun()

st.divider()

# --- VISUALIZZAZIONE RISULTATI ---
if len(st.session_state.history) > 5:
    h = st.session_state.history
    z_scores, h_tot, h_rec, runs, ww_status, markov = calculate_metrics(h)
    
    last_spin = h[0]
    
    # --- MOTORE PREDITTIVO IBRIDO ---
    # Unisce la memoria di Markov (70%) con il riequilibrio dello Z-Score (30%)
    m_probs = markov.loc[last_spin].values
    
    # Se uno Z-Score è molto negativo (ritardo), aumenta leggermente il peso per il riequilibrio naturale
    bias_weights = np.array([max(0.01, THEORETICAL_PROBS[s] - z_scores[s]*0.015) for s in SEGMENTS])
    
    final_probs = (m_probs * 0.7) + (bias_weights * 0.3)
    final_probs /= final_probs.sum() # Normalizziamo a 100%
    
    pred_df = pd.Series(final_probs, index=SEGMENTS).sort_values(ascending=False)
    top_3 = pred_df.head(3)
    
    st.success(f"🎯 **PREVISIONE ALGORITMICA DOPO '{last_spin}':**\n\n" + 
               " | ".join([f"**{k}** ({v:.1%})" for k, v in top_3.items()]))

    # --- METRICHE AVANZATE ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Entropia L/T", f"{h_tot:.2f}", help="Caos generale. Più è basso, più il gioco è prevedibile.")
    m2.metric("Entropia B/T", f"{h_rec:.2f}", delta=f"{h_rec - h_tot:.2f}", delta_color="inverse", help="Misura il cambio di ritmo del dealer.")
    m3.metric("Wald-Wolfowitz", f"{runs} Runs", delta=ww_status, delta_color="off")

    # --- TABELLE SICURE (Zero Crash) ---
    st.write("### 📊 Dettagli Matematici")
    t1, t2 = st.tabs(["Transizioni (Markov)", "Ritardi e Frequenze (Z-Score)"])
    
    with t1:
        st.write(f"Probabilità storiche di transizione:")
        # Convertiamo in stringa con % per evitare crash di rendering grafico su Safari
        st.dataframe((markov * 100).round(1).astype(str) + "%", use_container_width=True)
        
    with t2:
        st.write("**Valori positivi** = Esce più del normale | **Valori negativi** = In ritardo statistico")
        z_df = pd.DataFrame(list(z_scores.items()), columns=["Segmento", "Z-Score"]).set_index("Segmento")
        st.dataframe(z_df.round(2), use_container_width=True)
        
else:
    st.info("💡 Inserisci almeno 6 risultati dal tastierino per inizializzare il motore di calcolo.")

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

# --- MOTORE MATEMATICO (Invariato e Perfetto) ---
def calculate_metrics(history):
    n = len(history)
    counts = Counter(history)
    
    # 1. Z-Score (Deviazioni)
    z_scores = {}
    for s in SEGMENTS:
        p = THEORETICAL_PROBS[s]
        expected = n * p
        variance = n * p * (1 - p)
        std_dev = np.sqrt(variance)
        z_scores[s] = (counts.get(s, 0) - expected) / std_dev if std_dev > 0 else 0
        
    # 2. Entropia (Caos)
    def calc_entropy(data):
        if not data: return 0.0
        c = Counter(data)
        probs = [c.get(s, 0) / len(data) for s in SEGMENTS]
        return -sum(p * np.log2(p) for p in probs if p > 0)
    
    h_total = calc_entropy(history)
    h_recent = calc_entropy(history[:20]) 
    
    # 3. Wald-Wolfowitz (Cluster)
    binary = [1 if x in ['Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time'] else 0 for x in history]
    runs = 1
    for i in range(1, len(binary)):
        if binary[i] != binary[i-1]: runs += 1
        
    n1, n2 = sum(binary), n - sum(binary)
    ww_status = "In calcolo..."
    if n1 > 0 and n2 > 0 and n > 2:
        exp_runs = ((2 * n1 * n2) / n) + 1
        var_runs = (2 * n1 * n2 * (2 * n1 * n2 - n)) / ((n**2) * (n - 1))
        if var_runs > 0:
            ww_z = (runs - exp_runs) / np.sqrt(var_runs)
            if ww_z < -1.96: ww_status = "Cluster (Ripetitivo)"
            elif ww_z > 1.96: ww_status = "Alternanza (Irregolare)"
            else: ww_status = "Casuale"

    # 4. Markov (Transizioni)
    matrix = pd.DataFrame(0.0, index=SEGMENTS, columns=SEGMENTS)
    h_rev = history[::-1] 
    for i in range(len(h_rev)-1):
        matrix.loc[h_rev[i], h_rev[i+1]] += 1
        
    row_sums = matrix.sum(axis=1).replace(0, 1)
    matrix_norm = matrix.div(row_sums, axis=0)
    
    return z_scores, h_total, h_recent, runs, ww_status, matrix_norm

# --- INTERFACCIA UTENTE (Ottimizzata per velocità visiva) ---
st.title("🧮 Crazy Time Pro")

# TASTIERINO
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
if col_undo.button("↩️ Annulla", use_container_width=True):
    if st.session_state.history:
        st.session_state.history.pop(0)
        st.rerun()
if col_reset.button("🗑️ Reset", use_container_width=True, type="primary"):
    st.session_state.history = []
    st.rerun()

st.divider()

# --- DASHBOARD STRATEGICA ---
if len(st.session_state.history) > 5:
    h = st.session_state.history
    z_scores, h_tot, h_rec, runs, ww_status, markov = calculate_metrics(h)
    last_spin = h[0]
    
    # Predizione Ibrida (Markov + Z-Score Bias)
    m_probs = markov.loc[last_spin].values
    bias_weights = np.array([max(0.01, THEORETICAL_PROBS[s] - z_scores[s]*0.015) for s in SEGMENTS])
    final_probs = (m_probs * 0.7) + (bias_weights * 0.3)
    final_probs /= final_probs.sum()
    pred_df = pd.Series(final_probs, index=SEGMENTS).sort_values(ascending=False)

    # 1. IL PODIO DELLE GIOCATE
    st.subheader(f"🎯 COSA GIOCARE DOPO IL '{last_spin}'")
    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric("🥇 1° Scelta", pred_df.index[0], f"{pred_df.values[0]:.1%}")
    col_p2.metric("🥈 2° Scelta", pred_df.index[1], f"{pred_df.values[1]:.1%}")
    col_p3.metric("🥉 Copertura", pred_df.index[2], f"{pred_df.values[2]:.1%}")

    st.write("---")

    # 2. STATO DEL GIOCO (Traduzione Visiva dell'Entropia)
    st.subheader("🚦 STATO DELLA RUOTA")
    col_stat1, col_stat2 = st.columns(2)
    
    with col_stat1:
        if h_rec < h_tot:
            st.success("🟢 **RITMO PREVEDIBILE**\n\nIl dealer sta seguendo un pattern. Affidati al Podio in alto.")
        else:
            st.warning("🔴 **RITMO CAOTICO**\n\nLa ruota è imprevedibile ora. Riduci le puntate o salta il turno.")
            
    with col_stat2:
        hot = [k for k, v in z_scores.items() if v > 1.2]
        cold = [k for k, v in z_scores.items() if v < -1.2]
        st.info(f"🔥 **CALDI:** {', '.join(hot) if hot else 'Nessuno'}")
        st.error(f"❄️ **FREDDI (In Ritardo):** {', '.join(cold) if cold else 'Nessuno'}")

    # 3. METRICHE AVANZATE E TABELLE MATEMATICHE NASCOSTE
    with st.expander("⚙️ APRI MATRICI E DATI GREZZI (Per Analisi Profonda)"):
        m1, m2, m3 = st.columns(3)
        m1.metric("Entropia Globale", f"{h_tot:.2f}")
        m2.metric("Entropia Recente", f"{h_rec:.2f}")
        m3.metric("Test WW", ww_status)
        
        t1, t2 = st.tabs(["Transizioni (Markov)", "Ritardi (Z-Score)"]) 
        with t1:
            st.write("Probabilità storica di cosa esce dopo ogni segmento:")
            st.dataframe((markov * 100).round(1).astype(str) + "%", use_container_width=True)
        with t2:
            st.write("Valori > 1.2 = Caldi | Valori < -1.2 = Freddi/Ritardo")
            z_df = pd.DataFrame(list(z_scores.items()), columns=["Segmento", "Z-Score"]).set_index("Segmento")
            st.dataframe(z_df.round(2), use_container_width=True)
else:
    st.info("💡 Inserisci almeno 6 risultati dal tastierino per sbloccare la Dashboard Predittiva.")

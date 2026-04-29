import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter
import math
import random

# --- CONFIGURAZIONE PROFESSIONALE ---
st.set_page_config(page_title='Oracle Pro v5 - Hybrid Engine', layout='wide', initial_sidebar_state="expanded")

# --- DATABASE RUOTA EUROPEA E SETTORI ---
WHEEL = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
RED_NUMS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
SECTORS = {
    'Voisins': [22, 18, 29, 7, 28, 12, 35, 3, 26, 0, 32, 15, 19, 4, 21, 2, 25],
    'Tiers': [27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33],
    'Orphelins': [1, 20, 14, 31, 9, 17, 34, 6],
    'Zero': [12, 35, 3, 26, 0, 32, 15]
}
EXPECTED_FREQ = {'Voisins': 17/37, 'Tiers': 12/37, 'Orphelins': 8/37, 'Zero': 7/37}

# Generiamo 37 Micro-Cluster di 5 numeri per attacco di precisione
MICRO_CLUSTERS = {}
for i, n in enumerate(WHEEL):
    cluster = [WHEEL[(i-2)%37], WHEEL[(i-1)%37], n, WHEEL[(i+1)%37], WHEEL[(i+2)%37]]
    MICRO_CLUSTERS[n] = cluster

# --- STATO DELLA SESSIONE ---
session_vars = [
    ('history', []), ('total_spins', 0), ('dealer_spins', 0), 
    ('distances', []), ('bankroll', 1000), ('base_unit', 1)
]
for key, default in session_vars:
    if key not in st.session_state: 
        st.session_state[key] = default

# --- MOTORE MATEMATICO IBRIDO ---

def get_sfasamento(h, target_list):
    for i, val in enumerate(h):
        if val in target_list: return i     
    return len(h)

def calculate_rsi(binary_hist, period=14):
    if len(binary_hist) < period: return 50.0
    gains = sum(binary_hist[:period])
    rs = (gains / period) / ((period - gains) / period) if (period - gains) != 0 else 999
    return 100 - (100 / (1 + rs))

def get_advanced_analysis(h):
    # 1. Analisi Markoviana Settori Classici
    matrix = pd.DataFrame(0.0, index=SECTORS.keys(), columns=SECTORS.keys())
    sec_h = [next((s for s, nums in SECTORS.items() if x in nums), 'Voisins') for x in h]
    for i in range(len(sec_h)-1, 0, -1):
        weight = math.exp(-0.07 * (len(sec_h) - 1 - i))
        matrix.loc[sec_h[i], sec_h[i-1]] += weight
    m_norm = matrix.div(matrix.sum(axis=1).replace(0, 1), axis=0)

    # 2. Ricerca Micro-Cluster Dominante (Edge detection)
    best_cluster = None
    max_edge = 0
    for center, nums in MICRO_CLUSTERS.items():
        binary = [1 if x in nums else 0 for x in h[:20]]
        prob = sum([v * math.exp(-0.1 * i) for i, v in enumerate(binary)]) / sum([math.exp(-0.1 * i) for i in range(20)])
        rsi = calculate_rsi([1 if x in nums else 0 for x in h])
        if rsi > 70: prob *= 1.15 # Momentum
        if prob > max_edge:
            max_edge = prob
            best_cluster = center
            
    return m_norm, best_cluster, max_edge

def get_parity_bias(h):
    recent = ["Pari" if (x % 2 == 0 and x != 0) else "Dispari" for x in h[:20] if x != 0]
    if not recent: return "N/A", 0.5
    counts = Counter(recent)
    fav = counts.most_common(1)[0]
    return fav[0], fav[1] / len(recent)

def kelly_bet(win_prob, bankroll, base_unit):
    b = 6.2 # Quota netta per 5 numeri (31/5)
    if win_prob <= (5/37): return 0
    kf = ((win_prob * b) - (1 - win_prob)) / b
    return max(0, round((bankroll * (kf / 2)) / (base_unit * 5))) * 5

# --- INTERFACCIA ---
st.title(' Oracle Hybrid Pro v5')

# Telemetria Superiore
c_t1, c_t2, c_t3, c_t4 = st.columns(4)
st.session_state.bankroll = c_t1.number_input("Bankroll", value=st.session_state.bankroll)
c_t2.metric("Giri Totali", st.session_state.total_spins)
c_t3.metric("Trend Parità", get_parity_bias(st.session_state.history)[0])
c_t4.metric("Unità Base", f"{st.session_state.base_unit}€")

# Inserimento Numeri
st.markdown("### 🎲 Inserimento Risultati")
cols = st.columns(12)
for i in range(1, 37):
    with cols[(i-1)%12]:
        if st.button(str(i), key=f'n{i}', use_container_width=True):
            if st.session_state.history:
                st.session_state.distances.insert(0, abs(WHEEL.index(st.session_state.history[0]) - WHEEL.index(i)))
            st.session_state.history.insert(0, i)
            st.session_state.total_spins += 1
            st.rerun()

if st.button('0 - ZERO', use_container_width=True, type='primary'):
    st.session_state.history.insert(0, 0)
    st.session_state.total_spins += 1
    st.rerun()

# --- ANALISI E ATTACCO ---
if len(st.session_state.history) > 10:
    h = st.session_state.history
    markov, b_cluster, edge = get_advanced_analysis(h)
    last_sec = next((s for s, nums in SECTORS.items() if h[0] in nums), 'Voisins')
    
    st.markdown("---")
    st.markdown("## 🎯 STRATEGIA DI ATTACCO")
    
    col_l, col_r = st.columns([2, 1])
    
    with col_l:
        bet_size = kelly_bet(edge, st.session_state.bankroll, st.session_state.base_unit)
        if bet_size > 0 and edge > 0.18:
            nums = MICRO_CLUSTERS[b_cluster]
            st.markdown(f"""
                <div style="background:#065f46; padding:25px; border-radius:15px; border:2px solid #10b981; text-align:center;">
                    <h1 style="color:white; margin:0;">PUNTA: {bet_size} PEZZI</h1>
                    <h2 style="color:#a7f3d0;">Micro-Cluster {b_cluster} e vicini</h2>
                    <p style="font-size:24px; color:white; font-weight:bold;">{nums}</p>
                    <p style="color:#d1fae5;">Edge Calcolato: {edge:.1%} | Strategia: Kelly Optimized</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ ATTENDERE: Vantaggio statistico insufficiente per un attacco sicuro.")

    with col_r:
        st.write("### 📊 Macro Settori")
        st.dataframe(markov.loc[last_sec].sort_values(ascending=False).to_frame("% Prob").style.background_gradient(cmap='Greens'), use_container_width=True)

    # Dettagli Tecnici Inferiori
    st.markdown("### 🔍 Telemetria Avanzata")
    sd1, sd2, sd3 = st.columns(3)
    with sd1:
        st.write("**Dealer Signature**")
        if st.session_state.distances:
            common = Counter(st.session_state.distances[:10]).most_common(1)[0]
            st.metric("Salto Dominante", f"+{common[0]}", f"{common[1]*10}% costanza")
    with sd2:
        st.write("**Urgenza Settori (Gap)**")
        for s in SECTORS:
            gap = get_sfasamento(h, SECTORS[s])
            st.write(f"{s}: **{gap}** (Atteso {round(1/EXPECTED_FREQ[s])})")
    with sd3:
        st.write("**Analisi RSI**")
        rsi_val = calculate_rsi([1 if x in SECTORS['Voisins'] else 0 for x in h])
        st.progress(rsi_val/100, text=f"RSI Voisins: {rsi_val:.1f}")

# Cronologia
if st.session_state.history:
    st.markdown("---")
    h_display = st.columns(min(len(st.session_state.history), 20))
    for col, val in zip(h_display, st.session_state.history[:20]):
        bg = '#ef4444' if val in RED_NUMS else ('#10b981' if val == 0 else '#1f2937')
        col.markdown(f'<div style="background:{bg}; color:white; border-radius:5px; text-align:center; padding:5px; font-weight:bold;">{val}</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ System")
    st.session_state.base_unit = st.number_input("Valore Pezzo (€)", value=st.session_state.base_unit)
    if st.button("↩️ Cancella Ultimo"):
        if st.session_state.history: st.session_state.history.pop(0); st.rerun()
    if st.button("🗑️ Reset Sessione", type="primary"):
        st.session_state.history = []; st.session_state.total_spins = 0; st.rerun()

import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter
import math

# --- CONFIGURAZIONE PROFESSIONALE ---
st.set_page_config(page_title='Roulette Oracle Pro v4', layout='wide')

# Database Ruota Europea e Settori
WHEEL = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
RED_NUMS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
SECTORS = {
    'Voisins': [22, 18, 29, 7, 28, 12, 35, 3, 26, 0, 32, 15, 19, 4, 21, 2, 25],
    'Tiers': [27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33],
    'Orphelins': [1, 20, 14, 31, 9, 17, 34, 6],
    'Zero': [12, 35, 3, 26, 0, 32, 15]
}
EXPECTED_FREQ = {'Voisins': 17/37, 'Tiers': 12/37, 'Orphelins': 8/37, 'Zero': 7/37}

# --- STATO DELLA SESSIONE ---
for key, default in [('history', []), ('total_spins', 0), ('dealer_spins', 0), ('dealer_history', []), ('distances', [])]:
    if key not in st.session_state: 
        st.session_state[key] = default

# --- MOTORE MATEMATICO ---
def get_sfasamento(h, target_list):
    for i, val in enumerate(h):
        if val in target_list: return i     
    return len(h)

def get_analysis_weighted(h):
    # Matrice di Markov pesata con decadimento esponenziale
    n = len(h)
    matrix = pd.DataFrame(0.0, index=SECTORS.keys(), columns=SECTORS.keys())
    sec_h = [next((s for s, nums in SECTORS.items() if x in nums), 'Voisins') for x in h]
    for i in range(len(sec_h)-1, 0, -1):
        age = len(sec_h) - 1 - i
        weight = math.exp(-0.07 * age)
        matrix.loc[sec_h[i], sec_h[i-1]] += weight
    m_norm = matrix.div(matrix.sum(axis=1).replace(0, 1), axis=0)
    
    def entropy(data):
        if not data: return 0.0
        c = Counter(data)
        probs = [v / len(data) for v in c.values()]
        return -sum(p * math.log2(p) for p in probs if p > 0)
    
    return m_norm, entropy(sec_h), entropy(sec_h[:15])

def get_parity_bias(h):
    if not h: return "N/A", 0.5
    recent = ["Pari" if (x % 2 == 0 and x != 0) else "Dispari" for x in h[:20] if x != 0]
    if not recent: return "N/A", 0.5
    counts = Counter(recent)
    fav = counts.most_common(1)[0]
    return fav[0], fav[1] / len(recent)

def get_chi_square(h):
    # Test statistico per Bias della ruota
    if len(h) < 15: return None
    counts = Counter([next((s for s, nums in SECTORS.items() if x in nums), 'Voisins') for x in h])
    return sum(((counts.get(s, 0) - EXPECTED_FREQ[s]*len(h))**2 / (EXPECTED_FREQ[s]*len(h)) for s in SECTORS))

def get_composite_score(h, sector, markov_prob, parity_match):
    # Algoritmo di punteggio composito
    sfas = get_sfasamento(h, SECTORS[sector])
    exp_gap = 1 / EXPECTED_FREQ[sector]
    sfas_score = min(sfas / exp_gap, 2.0) / 2.0
    parity_bonus = 0.15 if parity_match else 0.0
    return (0.40 * markov_prob + 0.35 * sfas_score + 0.10 * parity_bonus)

# --- INTERFACCIA UTENTE ---
st.title(' Roulette Oracle Pro v4')

# Telemetria Superiore
c1, c2, c3, c4, c5 = st.columns([2,1,1,1,1])
current_rtp = c1.number_input('RTP Live (%)', value=97.3, step=0.1)
c2.metric('Giri Tot.', st.session_state.total_spins)
c3.metric('Giri Dealer', st.session_state.dealer_spins)
chi2_val = get_chi_square(st.session_state.history)
if chi2_val: 
    c5.metric('Chi2 Bias', f'{chi2_val:.1f}', delta='BIAS' if chi2_val > 7.8 else 'OK')

# Tastiera Numerica
st.write('### Inserisci Risultato')
cols_btn = st.columns(12)
for i in range(1, 37):
    with cols_btn[(i-1)%12]:
        if st.button(str(i), key=f'btn{i}', use_container_width=True):
            if st.session_state.history:
                d = abs(WHEEL.index(st.session_state.history[0]) - WHEEL.index(i))
                st.session_state.distances.insert(0, d)
            st.session_state.history.insert(0, i)
            st.session_state.dealer_history.insert(0, i)
            st.session_state.total_spins += 1
            st.session_state.dealer_spins += 1
            st.rerun()

if st.button('0 - ZERO', use_container_width=True, type='primary'):
    st.session_state.history.insert(0, 0)
    st.session_state.total_spins += 1
    st.rerun()

# Cronologia Visiva
if st.session_state.history:
    st.markdown('---')
    h_cols = st.columns(min(len(st.session_state.history), 20))
    for col, val in zip(h_cols, st.session_state.history[:20]):
        bg = '#c0392b' if val in RED_NUMS else ('#27ae60' if val == 0 else '#2c3e50')
        col.markdown(f'<div style="background:{bg}; color:white; border-radius:5px; text-align:center; padding:5px; font-weight:bold;">{val}</div>', unsafe_allow_html=True)

# LOGICA DI DECISIONE
if len(st.session_state.history) > 5:
    h = st.session_state.history
    markov, ent_total, ent_recent = get_analysis_weighted(h)
    last_sec = next((s for s, nums in SECTORS.items() if h[0] in nums), 'Voisins')
    p_trend, p_strength = get_parity_bias(h)
    
    best_sector = None
    max_score = -1
    for sec in SECTORS.keys():
        prob = markov.loc[last_sec].get(sec, 0)
        sec_nums = SECTORS[sec]
        parity_match = any((n % 2 == 0) if p_trend == "Pari" else (n % 2 != 0) for n in sec_nums)
        score = get_composite_score(h, sec, prob, parity_match)
        if score > max_score:
            max_score = score
            best_sector = sec

    # Box Decisione
    st.markdown('## PROSSIMA PUNTATA')
    if ent_recent > 2.2:
        st.error(f"ATTENDI: Entropia Alta ({ent_recent:.2f}). Sequenza caotica.")
    else:
        box_color = '#581c87' if max_score > 0.6 else '#1e3a5f'
        azione = "ATTACCO" if max_score > 0.6 else "MONITORAGGIO"
        st.markdown(f"""
            <div style="background:{box_color}; padding:20px; border-radius:12px; border:2px solid #ffffff33;">
                <h2 style="color:white; margin:0;">{azione}: {best_sector.upper()} </h2>
                <p style="color:#ffffffcc; font-size:18px;">Trend Parità: <b> {p_trend} ({p_strength:.0%})</b>. 
                Filtro applicato: Punta preferibilmente i {p_trend} di {best_sector}.</p>
            </div>
        """, unsafe_allow_html=True)

    # Dettagli Analisi
    sig1, sig2, sig3 = st.columns(3)
    with sig1:
        st.write("### Markov Sectors")
        st.dataframe(markov.loc[last_sec].sort_values(ascending=False), use_container_width=True)
    with sig2:
        st.write("### Urgenza Settori")
        for s in SECTORS:
            gap = get_sfasamento(h, SECTORS[s])
            st.write(f"{s}: Gap {gap} (Atteso {round(1/EXPECTED_FREQ[s])})")
    with sig3:
        st.write("### Dealer Signature")
        if st.session_state.distances:
            common_dist = Counter(st.session_state.distances[:10]).most_common(1)[0]
            st.metric("Salto Dominante", f"+{common_dist[0]}", f"{common_dist[1]*10}% costanza")

# SIDE

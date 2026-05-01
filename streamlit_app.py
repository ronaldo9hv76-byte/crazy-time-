import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter
import math

# --- CONFIGURAZIONE UI APPLE DARK PRO ---
st.set_page_config(page_title='Oracle Fusion v5.1', layout='wide', initial_sidebar_state='expanded')

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #F5F5F7; font-family: -apple-system, sans-serif; }
    .glass-box { background: rgba(28, 28, 30, 0.7); backdrop-filter: blur(15px); border-radius: 18px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 15px; }
    .action-box { background: linear-gradient(145deg, #1C1C1E 0%, #2C2C2E 100%); border-radius: 24px; padding: 30px; border: 1px solid #3A3A3C; box-shadow: 0 20px 40px rgba(0,0,0,0.6); }
    .numpad-btn>button { border-radius: 10px; background-color: #1C1C1E; color: white; border: 1px solid #3A3A3C; height: 50px; font-weight: 700; transition: 0.2s; font-size: 18px; }
    .numpad-btn>button:hover { border-color: #0A84FF; background: #2C2C2E; transform: scale(1.02); }
    .btn-red>button { border-bottom: 4px solid #FF3B30; }
    .btn-black>button { border-bottom: 4px solid #8E8E93; }
    .btn-zero>button { border-bottom: 4px solid #32D74B; background-color: rgba(50, 215, 75, 0.1); }
    .highlight-num { background: #0A84FF; color: white; padding: 8px 14px; border-radius: 8px; font-weight: bold; margin: 4px; display: inline-block; font-size: 18px; }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE RUOTA EUROPEA ---
WHEEL = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
RED_NUMS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
SECTORS = {
    'Voisins': [22, 18, 29, 7, 28, 12, 35, 3, 26, 0, 32, 15, 19, 4, 21, 2, 25],
    'Tiers': [27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33],
    'Orphelins': [1, 20, 14, 31, 9, 17, 34, 6],
    'Zero': [12, 35, 3, 26, 0, 32, 15]
}

# --- STATO SESSIONE ---
for key, def_val in [('history', []), ('distances', []), ('wins', 0), ('losses', 0)]:
    if key not in st.session_state: st.session_state[key] = def_val

# --- MOTORE MATEMATICO FUSION ---
def get_parity(n): 
    if n == 0: return 'Zero'
    return 'Pari' if n % 2 == 0 else 'Dispari'

def get_entropy(data):
    if not data: return 0.0
    c = Counter(data)
    probs = [v / len(data) for v in c.values()]
    return -sum(p * math.log2(p) for p in probs if p > 0)

def get_weighted_analysis(h):
    if len(h) < 5: return None, 0
    sec_h = [next((s for s, nums in SECTORS.items() if x in nums), 'Voisins') for x in h]
    matrix = pd.DataFrame(0.0, index=SECTORS.keys(), columns=SECTORS.keys())
    
    # Decadimento esponenziale corretto
    for i in range(len(sec_h)-1, 0, -1):
        weight = math.exp(-0.08 * (len(sec_h)-1-i))
        matrix.loc[sec_h[i], sec_h[i-1]] += weight
        
    m_norm = matrix.div(matrix.sum(axis=1).replace(0, 1), axis=0)
    ent = get_entropy(h[:15])
    return m_norm, ent

def get_5_numbers(pivot_num, target_parity):
    # Calcola i 5 vicini fisici sul cilindro e filtra per parità dominante
    try:
        idx = WHEEL.index(pivot_num)
        indices = [(idx + i) % 37 for i in range(-2, 3)]
        neighbors = [WHEEL[i] for i in indices]
        
        # Ordina: prima quelli della parità target, poi gli altri
        fav = [n for n in neighbors if get_parity(n) == target_parity]
        others = [n for n in neighbors if get_parity(n) != target_parity]
        return (fav + others)[:5]
    except: return [0, 32, 15, 19, 4]

def add_spin(val):
    if st.session_state.history:
        # Distanza in senso orario sul cilindro
        d = (WHEEL.index(val) - WHEEL.index(st.session_state.history[0])) % 37
        st.session_state.distances.insert(0, d)
    st.session_state.history.insert(0, val)
    st.rerun()

# --- UI DASHBOARD ---
st.title(" Oracle Fusion v5.1 | Professional System")

# Metriche Superiori
m1, m2, m3 = st.columns(3)
m1.metric("Giri Registrati", len(st.session_state.history))
m2.metric("Stato Analisi", "🔴 CALIBRAZIONE" if len(st.session_state.history) < 20 else "🟢 MOTORE STABILE")
acc = (st.session_state.wins / max(1, st.session_state.wins + st.session_state.losses)) * 100
m3.metric("Precisione Virtuale", f"{acc:.1f}%")

st.markdown("---")
col_input, col_analisi = st.columns([1, 2])

with col_input:
    st.markdown("### ⌨️ Layout Tappeto")
    # Tasto ZERO
    st.markdown('<div class="btn-zero numpad-btn">', unsafe_allow_html=True)
    if st.button("0 - ZERO", use_container_width=True): add_spin(0)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Griglia 1-36 (Esatto layout roulette: 12 righe, 3 colonne)
    for r in range(12):
        c1, c2, c3 = st.columns(3)
        for c, col in enumerate([c1, c2, c3]):
            val = r * 3 + c + 1
            cl = "btn-red" if val in RED_NUMS else "btn-black"
            with col:
                st.markdown(f'<div class="{cl} numpad-btn">', unsafe_allow_html=True)
                if st.button(str(val), key=f'btn_{val}', use_container_width=True):
                    add_spin(val)
                st.markdown('</div>', unsafe_allow_html=True)

with col_analisi:
    # NASTRO RECENTI
    if st.session_state.history:
        recent = st.session_state.history[:12]
        st.markdown('<div style="display:flex; overflow-x:auto; padding:10px 0;">' + "".join([
            f'<div style="background:{"#32D74B" if v==0 else ("#FF3B30" if v in RED_NUMS else "#2C2C2E")}; border-radius:50%; width:35px; height:35px; display:flex; align-items:center; justify-content:center; margin-right:6px; font-weight:bold; color:white; border:2px solid rgba(255,255,255,0.2);">{v}</div>' for v in recent
        ]) + '</div>', unsafe_allow_html=True)

    # --- ANALISI E DECISIONE FINALE ---
    if len(st.session_state.history) > 10:
        h = st.session_state.history
        markov, entropy = get_weighted_analysis(h)
        
        # 1. Trend Parità
        recent_p = [get_parity(n) for n in h[:15] if n != 0]
        p_trend = Counter(recent_p).most_common(1)[0][0] if recent_p else "Pari"
        
        # 2. Firma Dealer
        sig_dist = Counter(st.session_state.distances[:15]).most_common(1)[0][0] if st.session_state.distances else 0
        pivot = WHEEL[(WHEEL.index(h[0]) + sig_dist) % 37]
        
        # 3. Settore Markov
        last_sec = next((s for s, nums in SECTORS.items() if h[0] in nums), 'Voisins')
        best_sec = markov.loc[last_sec].idxmax()
        
        # I 5 NUMERI TARGET
        final_5 = get_5_numbers(pivot, p_trend)
        
        # ACTION BOX
        box_color = "linear-gradient(145deg, #051937, #004d7a)" if entropy < 2.0 else "linear-gradient(145deg, #1C1C1E, #2C2C2E)"
        st.markdown(f"""
            <div class="action-box" style="background: {box_color}">
                <h5 style="color:#0A84FF; margin:0;">🎯 TARGET IDENTIFICATO</h5>
                <h1 style="color:white; margin:10px 0;">{best_sec.upper()} + {p_trend.upper()}</h1>
                <p style="font-size:18px; color:#F5F5F7; margin-bottom:5px;">I 5 Numeri ad alta probabilità fisica:</p>
                <div>
                    {' '.join([f'<span class="highlight-num">{n}</span>' for n in final_5])}
                </div>
                <p style="margin-top:15px; font-size:14px; opacity:0.7;">Analisi: Salto tattico previsto di +{sig_dist} caselle. Entropia di rottura a {entropy:.2f}.</p>
            </div>
        """, unsafe_allow_html=True)

        # TELEMETRIA
        st.markdown("<br>", unsafe_allow_html=True)
        t1, t2 = st.columns(2)
        with t1:
            st.markdown('<div class="glass-box">', unsafe_allow_html=True)
            st.write("### 🧬 Parità")
            st.write(f"Trend: **{p_trend}**")
            st.write("Le estrazioni stanno compensando il lato opposto.")
            st.markdown('</div>', unsafe_allow_html=True)
        with t2:
            st.markdown('<div class="glass-box">', unsafe_allow_html=True)
            st.write("### ⚙️ Dealer")
            st.write(f"Salto Medio: **+{sig_dist} pockets**")
            st.write(f"Pivot Previsto: **{pivot}**")
            st.markdown('</div>', unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.markdown("## ⚙️ Settings Oracle")
if st.sidebar.button("⏪ Annulla Ultimo Errore", use_container_width=True):
    if st.session_state.history: 
        st.session_state.history.pop(0)
        if st.session_state.distances: st.session_state.distances.pop(0)
        st.rerun()

if st.sidebar.button("👤 Cambio Dealer (Reset Fisica)", use_container_width=True):
    st.session_state.distances = []
    st.sidebar.success("Fisica braccio resettata.")
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Reset Intera Sessione", use_container_width=True):
    for key in ['history', 'distances', 'wins', 'losses']: 
        st.session_state[key] = [] if isinstance(st.session_state[key], list) else 0
    st.rerun()

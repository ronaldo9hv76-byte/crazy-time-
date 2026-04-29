import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter
import math

# --- CONFIGURAZIONE ---
st.set_page_config(page_title='Roulette Oracle Pro v1', layout='wide', initial_sidebar_state='expanded')

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #F5F5F7; font-family: "SF Pro Display", sans-serif; }
    .glass-box { background: rgba(28, 28, 30, 0.65); backdrop-filter: blur(10px); border-radius: 16px; padding: 20px; border: 1px solid rgba(255, 255, 255, 0.08); margin-bottom: 12px; }
    .action-box { background: linear-gradient(145deg, #1C1C1E 0%, #2C2C2E 100%); border-radius: 20px; padding: 25px; border: 1px solid #3A3A3C; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .numpad-btn>button { border-radius: 8px; background-color: #1C1C1E; color: white; border: 1px solid #3A3A3C; height: 50px; font-size: 18px; font-weight: bold; }
    .numpad-btn>button:hover { border-color: #0A84FF; transform: scale(1.05); }
    .btn-red>button { border-bottom: 3px solid #FF3B30; }
    .btn-black>button { border-bottom: 3px solid #8E8E93; }
    .btn-zero>button { border-bottom: 3px solid #32D74B; }
    .text-green { color: #32D74B; } .text-orange { color: #FF9F0A; } .text-red { color: #FF3B30; }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE FISICO DELLA RUOTA (EUROPEA) ---
WHEEL_ORDER = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
RED_NUMS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

# SETTORI FRANCESI
SECTORS = {
    'Zero': [12, 35, 3, 26, 0, 32, 15],
    'Voisins': [22, 18, 29, 7, 28, 12, 35, 3, 26, 0, 32, 15, 19, 4, 21, 2, 25],
    'Tiers': [27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33],
    'Orphelins': [1, 20, 14, 31, 9, 17, 34, 6]
}

# --- INIT STATE ---
for key in ['history', 'sector_history', 'distances']:
    if key not in st.session_state: st.session_state[key] = []
for key in ['total_spins', 'wins', 'losses']:
    if key not in st.session_state: st.session_state[key] = 0
if 'last_prediction' not in st.session_state: st.session_state['last_prediction'] = None

# --- FUNZIONI CORE ---
def get_color(num): return 'Green' if num == 0 else ('Red' if num in RED_NUMS else 'Black')
def get_dozen(num): return '0' if num == 0 else ('D1' if num <= 12 else ('D2' if num <= 24 else 'D3'))
def get_sector(num):
    for sec, nums in SECTORS.items():
        if num in nums: return sec
    return 'Unknown'

def get_wheel_distance(n1, n2):
    # Calcola la distanza fisica sul cilindro tra due numeri (0-18 pockets)
    i1, i2 = WHEEL_ORDER.index(n1), WHEEL_ORDER.index(n2)
    dist = abs(i1 - i2)
    return min(dist, 37 - dist) # Prende la via più breve (oraria o antioraria)

def update_tracker(num_uscito):
    if st.session_state.last_prediction:
        target_sector = st.session_state.last_prediction.get('sector')
        if get_sector(num_uscito) == target_sector:
            st.session_state.wins += 1
        else:
            st.session_state.losses += 1

def entropy(data):
    if not data: return 0.0
    c = Counter(data)
    probs = [v / len(data) for v in c.values()]
    return -sum(p * math.log2(p) for p in probs if p > 0)

def get_markov_sectors(sect_history):
    # Calcola la matrice di transizione per i settori fisici
    labels = ['Zero', 'Voisins', 'Tiers', 'Orphelins']
    matrix = pd.DataFrame(0.0, index=labels, columns=labels)
    n = len(sect_history)
    ent = entropy(sect_history[:15])
    decay = 0.15 if ent > 1.8 else 0.05 # Adattivo
    
    for i in range(n - 1, 0, -1):
        matrix.loc[sect_history[i], sect_history[i - 1]] += math.exp(-decay * (n - 1 - i))
    return matrix.div(matrix.sum(axis=1).replace(0, 1), axis=0), ent

def analyze_dealer_signature(distances):
    if len(distances) < 10: return None, 0
    c = Counter(distances[:20]) # Analizza gli ultimi 20 lanci
    most_common, count = c.most_common(1)[0]
    freq = count / len(distances[:20])
    return most_common, freq

def get_sfasamento(h, target, mode='dozen'):
    for i, val in enumerate(h):
        if mode == 'dozen' and get_dozen(val) == target: return i
        elif mode == 'sector' and get_sector(val) == target: return i
    return len(h)

# --- UI: DASHBOARD ---
st.title(" Roulette Oracle Pro | Physical Tracker")

# PERFORMANCE TRACKER
total_preds = st.session_state.wins + st.session_state.losses
accuracy = (st.session_state.wins / total_preds * 100) if total_preds > 0 else 0

st.markdown('<div class="glass-box" style="padding:10px 20px;">', unsafe_allow_html=True)
p1, p2, p3, p4 = st.columns(4)
p1.metric("Precisione Settore", f"{accuracy:.1f}%")
p2.metric("Vittorie (Win)", st.session_state.wins)
p3.metric("Errori (Loss)", st.session_state.losses)
p4.metric("Giri Inseriti", st.session_state.total_spins)
st.markdown('</div>', unsafe_allow_html=True)

# TASTIERA INPUT (Roulette Grid Rapida)
st.markdown("### ⌨️ Input Ruota")
st.markdown('<div class="numpad-btn">', unsafe_allow_html=True)
# Riga 0 isolata
c0, _ = st.columns([1, 8])
if c0.button("0", use_container_width=True, key="btn_0"):
    update_tracker(0)
    if st.session_state.history:
        st.session_state.distances.insert(0, get_wheel_distance(st.session_state.history[0], 0))
    st.session_state.history.insert(0, 0)
    st.session_state.sector_history.insert(0, get_sector(0))
    st.session_state.total_spins += 1
    st.rerun()

# Griglia 1-36 (3 colonne stile tappeto)
nums = [[1,2,3], [4,5,6], [7,8,9], [10,11,12], [13,14,15], [16,17,18], 
        [19,20,21], [22,23,24], [25,26,27], [28,29,30], [31,32,33], [34,35,36]]

cols = st.columns(12)
for i, col_arr in enumerate(nums):
    with cols[i]:
        for n in col_arr:
            color_class = "btn-red" if n in RED_NUMS else "btn-black"
            st.markdown(f'<div class="{color_class}">', unsafe_allow_html=True)
            if st.button(str(n), use_container_width=True, key=f"btn_{n}"):
                update_tracker(n)
                if st.session_state.history:
                    st.session_state.distances.insert(0, get_wheel_distance(st.session_state.history[0], n))
                st.session_state.history.insert(0, n)
                st.session_state.sector_history.insert(0, get_sector(n))
                st.session_state.total_spins += 1
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# NASTRO CRONOLOGICO COLORATO
if st.session_state.history:
    recent = st.session_state.history[:20]
    st.markdown('<div style="display:flex; overflow-x:auto; padding-top:15px; padding-bottom:10px;">' + "".join([
        f'<div style="background:{"#32D74B" if v==0 else ("#FF3B30" if v in RED_NUMS else "#2C2C2E")}; border-radius:50%; width:40px; height:40px; display:flex; align-items:center; justify-content:center; margin-right:8px; font-weight:bold; font-size:18px; color:white; border:2px solid rgba(255,255,255,0.2);">{v}</div>' for v in recent
    ]) + '</div>', unsafe_allow_html=True)

st.markdown("---")

# MOTORE DI ANALISI
if len(st.session_state.history) > 10:
    h = st.session_state.history
    sh = st.session_state.sector_history
    last_num = h[0]
    last_sec = sh[0]
    
    markov_sec, ent_sec = get_markov_sectors(sh)
    preds_sec = markov_sec.loc[last_sec].sort_values(ascending=False)
    fav_sec = preds_sec.index[0] if preds_sec.iloc[0] > 0 else None
    
    sig_dist, sig_freq = analyze_dealer_signature(st.session_state.distances)
    
    # Gap Analisi Dozzine
    gap_d1, gap_d2, gap_d3 = get_sfasamento(h, 'D1'), get_sfasamento(h, 'D2'), get_sfasamento(h, 'D3')
    max_doz_gap = max(gap_d1, gap_d2, gap_d3)
    urg_doz = 'D1' if gap_d1 == max_doz_gap else ('D2' if gap_d2 == max_doz_gap else 'D3')

    # ELABORAZIONE AZIONE
    azione = "MONITORAGGIO"
    motivo = "Attendere allineamento pattern fisici."
    unita = "🚫 0 UNITÀ"
    
    # Trigger 1: Dealer Signature Trovata
    if sig_freq > 0.25 and sig_dist is not None:
        target_zone_index = (WHEEL_ORDER.index(last_num) + sig_dist) % 37 # Predice caduta basata su spostamento
        pred_num_phys = WHEEL_ORDER[target_zone_index]
        fav_sec = get_sector(pred_num_phys) # Sovrascrive Markov con la Fisica Pura
        azione = f"🎯 ATTACCO FISICO: {fav_sec.upper()}"
        motivo = f"Dealer Signature Rilevata: La pallina cade spesso a +{sig_dist} pockets. Copri zona di {pred_num_phys}."
        unita = "💰 3 UNITÀ (Punta i cavalli nel settore)"
    
    # Trigger 2: Markov Convergenza Settori (Se Entropia bassa)
    elif ent_sec < 1.7 and fav_sec:
        azione = f"🔮 ATTACCO SETTORE: {fav_sec.upper()}"
        motivo = f"Motore Fisico Prevedibile (Entropia {ent_sec:.2f}). Markov indica transizione verso {fav_sec}."
        unita = "💵 2 UNITÀ (Sui numeri del settore)"
        
    # Trigger 3: Collasso Dozzina
    elif max_doz_gap > 11:
        azione = f"🚨 RECUPERO DOZZINA: {urg_doz}"
        motivo = f"La Dozzina {urg_doz} è in sfasamento estremo (Manca da {max_doz_gap} giri). Intervento Matematico."
        unita = "🪙 1 UNITÀ (Copertura in progressione)"

    # Salva predizione
    if azione != "MONITORAGGIO":
        st.session_state.last_prediction = {'sector': fav_sec}
    else:
        st.session_state.last_prediction = None

    # UI ACTION BOX
    box_color = "linear-gradient(145deg, #1A472A 0%, #0F2A1A 100%)" if "ATTACCO" in azione else \
                "linear-gradient(145deg, #4A1942 0%, #2A0845 100%)" if "RECUPERO" in azione else \
                "linear-gradient(145deg, #1C1C1E 0%, #2C2C2E 100%)"
                
    st.markdown(f"""
        <div class="action-box" style="background: {box_color};">
            <h4 style="color:#ffffff99; margin:0; text-transform:uppercase; font-size:12px;">Comando Tattico Dealer</h4>
            <h2 style="color:white; margin:5px 0 10px 0; font-size:32px;">{azione}</h2>
            <p style="color:#ffffffcc; font-size:16px; margin:0 0 15px 0;">{motivo}</p>
            <div style="display:flex; gap:20px;">
                <div style="background:rgba(0,0,0,0.3); padding:10px 15px; border-radius:10px;">
                    <span style="color:#ffffff99; font-size:12px;">Gestione Bankroll</span><br>
                    <b style="color:#32D74B; font-size:16px;">{unita}</b>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # PANNELLI DI TELEMETRIA
    cA, cB, cC = st.columns(3)
    
    with cA:
        st.markdown('<div class="glass-box">', unsafe_allow_html=True)
        st.markdown("#### 🔭 Dealer Signature")
        if sig_dist is not None:
            st.metric("Salto Frequente (Pockets)", f"+{sig_dist}")
            st.progress(float(sig_freq))
            st.caption(f"Frequenza salto del braccio: {sig_freq:.1%}")
        else:
            st.write("Dati insufficienti o lanciatore caotico.")
        st.markdown('</div>', unsafe_allow_html=True)

    with cB:
        st.markdown('<div class="glass-box">', unsafe_allow_html=True)
        st.markdown("#### 🌐 Markov (Settori)")
        for sec, prob in preds_sec.items():
            if prob > 0:
                st.write(f"**{sec}** ({prob:.1%})")
                st.progress(float(prob))
        st.markdown('</div>', unsafe_allow_html=True)

    with cC:
        st.markdown('<div class="glass-box">', unsafe_allow_html=True)
        st.markdown("#### ⚖️ Legge del Terzo (Gap)")
        st.write(f"**Dozzina 1:** Manca da {gap_d1}")
        st.write(f"**Dozzina 2:** Manca da {gap_d2}")
        st.write(f"**Dozzina 3:** Manca da {gap_d3}")
        st.caption("Soglia di attacco superata a 11 giri vuoti.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.markdown("## ⚙️ Controlli Live")
if st.sidebar.button("⏪ Cancella Errore", use_container_width=True):
    if st.session_state.history:
        st.session_state.history.pop(0)
        st.session_state.sector_history.pop(0)
        if st.session_state.distances: st.session_state.distances.pop(0)
        st.session_state.total_spins -= 1
        st.rerun()

if st.sidebar.button("👤 Cambio Dealer (Reset Fisica)", use_container_width=True):
    st.session_state.distances = []
    st.sidebar.success("Fisica azzerata per il nuovo braccio.")
    st.rerun()

if st.sidebar.button("🗑️ Hard Reset", use_container_width=True):
    for key in ['history', 'sector_history', 'distances']: st.session_state[key] = []
    for key in ['total_spins', 'wins', 'losses']: st.session_state[key] = 0
    st.rerun()

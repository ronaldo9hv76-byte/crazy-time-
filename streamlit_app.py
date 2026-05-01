import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter
import math

# --- CONFIGURAZIONE UI APPLE DARK PRO ---
st.set_page_config(page_title='Roulette Quantum V6', layout='wide', initial_sidebar_state='collapsed')

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #F5F5F7; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .glass-box { background: rgba(28, 28, 30, 0.8); backdrop-filter: blur(20px); border-radius: 16px; padding: 22px; border: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 16px; }
    .action-box { background: linear-gradient(135deg, #161618 0%, #222224 100%); border-radius: 20px; padding: 25px; border: 1px solid #333; box-shadow: 0 10px 30px rgba(0,0,0,0.8); }
    .action-box-alert { background: linear-gradient(135deg, #0A2A4A 0%, #001122 100%); border-radius: 20px; padding: 25px; border: 1px solid #0A84FF; box-shadow: 0 10px 40px rgba(10,132,255,0.2); }
    .numpad-btn>button { border-radius: 8px; background-color: #1A1A1C; color: white; border: 1px solid #2C2C2E; height: 55px; font-weight: 700; font-size: 20px; transition: all 0.1s; }
    .numpad-btn>button:active { transform: scale(0.95); }
    .btn-red>button { border-bottom: 4px solid #FF3B30; }
    .btn-black>button { border-bottom: 4px solid #636366; }
    .btn-zero>button { border-bottom: 4px solid #32D74B; background-color: rgba(50, 215, 75, 0.05); }
    .num-badge { display: inline-block; width: 45px; height: 45px; line-height: 45px; text-align: center; border-radius: 50%; font-weight: bold; font-size: 18px; margin: 4px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
    .badge-red { background: #FF3B30; color: white; border: 2px solid #FF453A; }
    .badge-black { background: #1C1C1E; color: white; border: 2px solid #3A3A3C; }
    .badge-zero { background: #32D74B; color: black; border: 2px solid #28CD41; }
    .badge-target { background: #0A84FF; color: white; border: 2px solid #5E5CE6; transform: scale(1.1); font-size: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- COSTANTI DELLA FISICA ---
WHEEL = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
RED_NUMS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
SECTORS = {
    'Voisins': [22, 18, 29, 7, 28, 12, 35, 3, 26, 0, 32, 15, 19, 4, 21, 2, 25],
    'Tiers': [27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33],
    'Orphelins': [1, 20, 14, 31, 9, 17, 34, 6],
    'Zero': [12, 35, 3, 26, 0, 32, 15]
}

# --- STATO SESSIONE ---
if 'history' not in st.session_state:
    st.session_state.update({'history': [], 'distances': [], 'hits': 0, 'misses': 0, 'last_target': []})

# --- MOTORE INFORMATICO V6 ---
def get_color_class(n):
    return "badge-zero" if n == 0 else ("badge-red" if n in RED_NUMS else "badge-black")

def get_sector(n):
    for sec, nums in SECTORS.items():
        if n in nums: return sec
    return 'Voisins'

def calculate_entropy(data, window=15):
    if len(data) < window: return 0.0
    recent = data[:window]
    counts = Counter(recent)
    probs = [v / window for v in counts.values()]
    return -sum(p * math.log2(p) for p in probs if p > 0)

def find_density_cluster(distances, window=20):
    # Algoritmo di Clustering: Cerca la zona di 7 caselle col maggior numero di drop
    if len(distances) < 15: return None, 0.0
    recent_dist = distances[:window]
    
    max_density = 0
    best_center = 0
    
    # Scansiona tutte le possibili 37 distanze come "centri"
    for center in range(37):
        hits_in_window = 0
        # Conta quanti lanci cadono in un raggio di ±3 caselle (finestra di 7) dal centro
        for d in recent_dist:
            # Calcola distanza circolare tra 'd' e 'center'
            diff = min((d - center) % 37, (center - d) % 37)
            if diff <= 3:
                hits_in_window += 1
        
        density = hits_in_window / len(recent_dist)
        if density > max_density:
            max_density = density
            best_center = center
            
    return best_center, max_density

def get_physical_neighbors(pivot, spread=2):
    # Ritorna il pivot e i suoi N vicini fisici (es. spread=2 -> 5 numeri tot)
    idx = WHEEL.index(pivot)
    return [WHEEL[(idx + i) % 37] for i in range(-spread, spread + 1)]

def process_input(val):
    # 1. Update Performance Tracker
    if st.session_state.last_target:
        if val in st.session_state.last_target:
            st.session_state.hits += 1
        else:
            st.session_state.misses += 1

    # 2. Update Physics Engine
    if st.session_state.history:
        prev = st.session_state.history[0]
        dist = (WHEEL.index(val) - WHEEL.index(prev)) % 37
        st.session_state.distances.insert(0, dist)
        
    st.session_state.history.insert(0, val)
    st.rerun()

# --- UI DASHBOARD ---
st.title(" Quantum Oracle V6")

# HEADER METRICS
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
total_spins = len(st.session_state.history)
total_bets = st.session_state.hits + st.session_state.misses
win_rate = (st.session_state.hits / total_bets * 100) if total_bets > 0 else 0.0

col_m1.metric("Giri Registrati", total_spins)
col_m2.metric("Centri (Hits)", st.session_state.hits)
col_m3.metric("Errori (Miss)", st.session_state.misses)
col_m4.metric("Win Rate Netto", f"{win_rate:.1f}%")

st.markdown("---")

col_left, col_right = st.columns([1, 2.2])

# --- TASTIERA TAPPETO (Left) ---
with col_left:
    st.markdown("### 🎛️ Input Console")
    st.markdown('<div class="btn-zero numpad-btn">', unsafe_allow_html=True)
    if st.button("0", use_container_width=True): process_input(0)
    st.markdown('</div>', unsafe_allow_html=True)
    
    for r in range(12):
        c1, c2, c3 = st.columns(3)
        for i, col in enumerate([c1, c2, c3]):
            val = r * 3 + i + 1
            btn_class = "btn-red" if val in RED_NUMS else "btn-black"
            with col:
                st.markdown(f'<div class="{btn_class} numpad-btn">', unsafe_allow_html=True)
                if st.button(str(val), key=f'b_{val}', use_container_width=True):
                    process_input(val)
                st.markdown('</div>', unsafe_allow_html=True)
                
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Reset Dealer", type="secondary", use_container_width=True):
        st.session_state.distances = []
        st.rerun()

# --- MOTORE INFERENZIALE E OUTPUT (Right) ---
with col_right:
    # 1. NASTRO CRONOLOGICO
    if st.session_state.history:
        st.markdown("**Ultimi numeri:**")
        html_history = '<div style="display:flex; flex-wrap:wrap; margin-bottom:15px;">'
        for v in st.session_state.history[:14]:
            html_history += f'<div class="num-badge {get_color_class(v)}">{v}</div>'
        html_history += '</div>'
        st.markdown(html_history, unsafe_allow_html=True)

    # 2. CALCOLI QUANTUM
    if total_spins >= 15:
        ent_sec = calculate_entropy([get_sector(n) for n in st.session_state.history], window=15)
        
        # Analisi Cluster Fisico (Il Cuore V6)
        cluster_center, cluster_density = find_density_cluster(st.session_state.distances, window=20)
        
        # Logica di Attacco
        target_numbers = []
        azione = "ATTENDERE"
        motivo = "Il motore sta ricalibrando la deviazione standard del dealer."
        alert_mode = False
        
        # SOGLIA CRITICA: Se il dealer lancia il 35%+ delle volte in un cluster di 7 caselle, è una firma fortissima.
        if cluster_density >= 0.35 and ent_sec < 1.95:
            alert_mode = True
            azione = "ATTACCO FISICO"
            # Calcola il Pivot basato sull'ultimo numero + il salto medio del cluster
            last_num = st.session_state.history[0]
            pivot_idx = (WHEEL.index(last_num) + cluster_center) % 37
            pivot_num = WHEEL[pivot_idx]
            
            # Prende i 5 numeri (Pivot + 2 vicini per lato)
            target_numbers = get_physical_neighbors(pivot_num, spread=2)
            motivo = f"Firma Dealer rilevata. Salto di +{cluster_center} caselle con densità del {cluster_density*100:.0f}%. Coprire zona {pivot_num}."
            st.session_state.last_target = target_numbers # Salva per il tracker
            
        else:
            st.session_state.last_target = [] # Annulla tracking se non si punta

        # 3. ACTION BOX DINAMICA
        box_style = "action-box-alert" if alert_mode else "action-box"
        status_color = "#32D74B" if alert_mode else "#FF9F0A"
        
        st.markdown(f"""
            <div class="{box_style}">
                <h6 style="color:{status_color}; letter-spacing:1px; text-transform:uppercase; margin:0;">Status Motore: {azione}</h6>
                <p style="color:#A1A1A6; margin-top:5px; font-size:15px;">{motivo}</p>
        """, unsafe_allow_html=True)
        
        if alert_mode and target_numbers:
            st.markdown('<div style="margin-top:20px; margin-bottom:10px;"><span style="color:white; font-size:18px;">PUNTA I SEGUENTI 5 NUMERI:</span></div>', unsafe_allow_html=True)
            html_targets = '<div style="display:flex; gap:10px;">'
            for n in target_numbers:
                html_targets += f'<div class="num-badge {get_color_class(n)} badge-target">{n}</div>'
            html_targets += '</div>'
            st.markdown(html_targets, unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

        # 4. TELEMETRIA RAW
        st.markdown("<br>", unsafe_allow_html=True)
        t1, t2 = st.columns(2)
        with t1:
            st.markdown('<div class="glass-box">', unsafe_allow_html=True)
            st.write("#### 📡 Statistica Settoriale")
            st.write(f"**Entropia Settori:** {ent_sec:.2f} " + ("🟢 (Stabile)" if ent_sec < 1.95 else "🔴 (Caos)"))
            
            # Trend Parità Semplice (Solo Info)
            recent_parity = [n for n in st.session_state.history[:15] if n != 0]
            evens = sum(1 for n in recent_parity if n % 2 == 0)
            st.write(f"**Trend Parità (15g):** {int(evens/len(recent_parity)*100)}% Pari")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with t2:
            st.markdown('<div class="glass-box">', unsafe_allow_html=True)
            st.write("#### 🎯 Analisi Lancio (Clustering)")
            if cluster_center is not None:
                st.write(f"**Drop Point Ottimale:** +{cluster_center} caselle")
                st.write(f"**Concentrazione:** {cluster_density*100:.1f}% nel target")
                st.progress(float(cluster_density))
            st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.info("🟡 Inserire almeno 15 numeri per avviare il motore di clustering quantistico.")

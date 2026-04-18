import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter
import math

# Configurazione Pagina - Tema Scuro Nativo
st.set_page_config(page_title="CT Oracle Pro v2", layout="wide", initial_sidebar_state="expanded")

# --- CSS CUSTOM STILE APPLE DARK PRO ---
st.markdown("""
    <style>
    /* Sfondo generale e font */
    .stApp {
        background-color: #000000;
        color: #FFFFFF;
    }
    
    /* Box stile Apple (Glassmorphism) */
    .metric-container {
        background: rgba(28, 28, 30, 0.7);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 10px;
    }

    /* Colori diversi per sezioni */
    .section-motore { border-left: 5px solid #0A84FF; background: rgba(10, 132, 255, 0.05); }
    .section-markov { border-left: 5px solid #BF5AF2; background: rgba(191, 90, 242, 0.05); }
    .section-bonus { border-left: 5px solid #FF9F0A; background: rgba(255, 159, 10, 0.05); }
    .section-tattica { border-radius: 15px; padding: 15px; border: 1px solid #32D74B; }

    /* Bottoni stile Apple */
    .stButton>button {
        border-radius: 10px;
        background-color: #1C1C1E;
        color: white;
        border: 1px solid #3A3A3C;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        border-color: #0A84FF;
        background-color: #2C2C2E;
        transform: translateY(-2px);
    }
    
    /* Sidebar scura */
    [data-testid="stSidebar"] {
        background-color: #161617;
    }
    
    h1, h2, h3 {
        font-family: "SF Pro Display", "Helvetica Neue", sans-serif;
        letter-spacing: -0.5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- COSTANTI E LOGICA (INVARIATE) ---
SEGMENTS = ['1', '2', '5', '10', 'Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
BONUS_LIST = ['Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
EXPECTED_FREQ = {'1': 21/54, '2': 13/54, '5': 7/54, '10': 4/54, 'Coin Flip': 4/54, 'Pachinko': 2/54, 'Cash Hunt': 2/54, 'Crazy Time': 1/54}
NEIGHBORS = {'1': ['10', '2', '5', 'Coin Flip'], '2': ['1', '10', 'Crazy Time', '5'], '5': ['1', 'Pachinko', '2', 'Cash Hunt'], '10': ['1', '2', 'Coin Flip', 'Cash Hunt'], 'Coin Flip': ['1', '10', '2', '5'], 'Pachinko': ['5', '1', 'Crazy Time'], 'Cash Hunt': ['10', '5', '1'], 'Crazy Time': ['1', '5', 'Pachinko']}
CORRELATION_MAP = {'5': ['Pachinko', 'Cash Hunt'], '10': ['Coin Flip', 'Cash Hunt'], '2': ['Crazy Time', 'Coin Flip'], '1': ['Coin Flip', 'Pachinko']}

if 'history' not in st.session_state: st.session_state.history = []
if 'total_spins' not in st.session_state: st.session_state.total_spins = 0
if 'dealer_spins' not in st.session_state: st.session_state.dealer_spins = 0
if 'dealer_history' not in st.session_state: st.session_state.dealer_history = []

def is_bonus(outcome): return outcome in BONUS_LIST
def get_sfasamento(h, target=None):
    for i, val in enumerate(h):
        if target:
            if val == target: return i
        else:
            if is_bonus(val): return i
    return len(h)

def get_analysis_weighted(h):
    matrix = pd.DataFrame(0.0, index=SEGMENTS, columns=SEGMENTS)
    n = len(h)
    for i in range(n - 1, 0, -1):
        age = n - 1 - i
        weight = math.exp(-0.07 * age)
        matrix.loc[h[i], h[i - 1]] += weight
    m_norm = matrix.div(matrix.sum(axis=1).replace(0, 1), axis=0)
    def entropy(data):
        if not data: return 0.0
        c = Counter(data)
        probs = [v / len(data) for v in c.values()]
        return -sum(p * math.log2(p) for p in probs if p > 0)
    return m_norm, entropy(h), entropy(h[:15])

def get_hot_cold(h, window=20):
    recent = h[:window] if len(h) >= window else h
    if not recent: return {}, {}
    n = len(recent); counts = Counter(recent)
    hot, cold = {}, {}
    for seg in SEGMENTS:
        obs = counts.get(seg, 0) / n
        exp = EXPECTED_FREQ[seg]; dev = (obs - exp) / exp
        if dev > 0.30: hot[seg] = dev
        elif dev < -0.30: cold[seg] = dev
    return hot, cold

def get_chi_square(h, window=40):
    recent = h[:window] if len(h) >= window else h
    if len(recent) < 15: return None
    n = len(recent); counts = Counter(recent)
    return sum((counts.get(seg, 0) - EXPECTED_FREQ[seg] * n) ** 2 / (EXPECTED_FREQ[seg] * n) for seg in SEGMENTS)

def get_trend(h, seg, short=10, long=25):
    if len(h) < long: return 0.0
    fs = h[:short].count(seg) / short; fl = h[:long].count(seg) / long
    return (fs - fl) / fl if fl > 0 else 0.0

def get_composite_score(h, seg, markov_prob):
    if not h: return 0.0
    sfas = get_sfasamento(h, seg); exp_gap = 1 / EXPECTED_FREQ.get(seg, 0.1)
    sfas_score = min(sfas / exp_gap, 2.0) / 2.0
    trend = get_trend(h, seg); trend_score = max(0.0, min(trend + 0.5, 1.0))
    _, cold = get_hot_cold(h); cold_bonus = 0.2 if seg in cold else 0.0
    return (0.40 * markov_prob + 0.35 * sfas_score + 0.15 * trend_score + 0.10 * cold_bonus)

def get_micro_sfasamento(h, window=15):
    result = {}
    recent = h[:window] if len(h) >= window else h
    for seg in SEGMENTS:
        zona = [seg] + NEIGHBORS.get(seg, [])
        gaps = [i for i, v in enumerate(recent) if v in zona]
        result[seg] = gaps[0] if gaps else window
    return result

# --- INTERFACCIA ---
st.title(" CT Oracle Pro v2")

# TOP BAR METRICS
m1, m2, m3, m4, m5 = st.columns(5)
with m1: current_rtp = st.number_input("RTP Live %", value=96.0)
m2.metric("Giri Totali", st.session_state.total_spins)
m3.metric("Giri Dealer", st.session_state.dealer_spins)
sfas_gen = get_sfasamento(st.session_state.history) if st.session_state.history else 0
m4.metric("Sfas. Bonus", sfas_gen)
chi2 = get_chi_square(st.session_state.history) if len(st.session_state.history) >= 15 else None
if chi2 is not None:
    m5.metric("Chi2 Bias", f"{chi2:.1f}", delta="BIAS" if chi2 > 14.07 else "RANDOM")

st.markdown("---")

# TASTIERA INPUT
st.markdown("### ⌨️ Inserimento Rapido")
cols_btn = st.columns(8)
for idx, seg in enumerate(SEGMENTS):
    if cols_btn[idx].button(seg, use_container_width=True):
        st.session_state.history.insert(0, seg)
        st.session_state.dealer_history.insert(0, seg)
        st.session_state.total_spins += 1
        st.session_state.dealer_spins += 1
        st.rerun()

# STORICO (NASTRO)
if st.session_state.history:
    recent20 = st.session_state.history[:20]
    st.markdown('<div style="display: flex; overflow-x: auto; padding: 10px;">' + "".join([
        f'<div style="background:{"#FF3B30" if is_bonus(v) else "#3A3A3C"}; border-radius:8px; padding:5px 10px; margin-right:5px; font-weight:bold; min-width:60px; text-align:center;">{v[:4] if is_bonus(v) else v}</div>' for v in recent20
    ]) + '</div>', unsafe_allow_html=True)

st.markdown("---")

# ANALISI PRINCIPALE
if len(st.session_state.history) > 5:
    h = st.session_state.history
    markov, ent_total, ent_recent = get_analysis_weighted(h)
    last = h[0]
    micro_sfas = get_micro_sfasamento(h)

    col1, col2, col3 = st.columns([1, 1.2, 1.3])

    with col1:
        st.markdown('<div class="metric-container section-motore">', unsafe_allow_html=True)
        st.subheader("📡 Motore")
        st.metric("Entropia Recente", f"{ent_recent:.2f}")
        if ent_recent < 1.85: st.success("PUNTUALE")
        elif ent_recent < 2.2: st.warning("INTERMEDIO")
        else: st.error("CAOTICO")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-container section-markov">', unsafe_allow_html=True)
        st.subheader("🔮 Markov Pro")
        preds = markov.loc[last].sort_values(ascending=False).head(4)
        for val, prob in preds.items():
            if prob > 0:
                score = get_composite_score(h, val, prob)
                st.write(f"**{val}** (Score: {score:.2f})")
                st.progress(float(prob))
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-container section-bonus">', unsafe_allow_html=True)
        st.subheader("🚀 Radar Bonus")
        bonus_data = []
        for b in BONUS_LIST:
            s = get_sfasamento(h, b)
            urg = s / (1/EXPECTED_FREQ[b])
            bonus_data.append((b, s, urg))
        bonus_data.sort(key=lambda x: x[2], reverse=True)
        for b, s, u in bonus_data:
            color = "#FF3B30" if u > 1.8 else "#FF9F0A" if u > 1.0 else "#32D74B"
            st.markdown(f"<span style='color:{color}; font-weight:bold;'>{b}</span>: Gap {s} (Urg: {u:.1f}x)", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # TATTICA FINALE
    st.markdown('<div class="section-tattica">', unsafe_allow_html=True)
    st.subheader("📋 Piano d'Azione")
    top_b, _, top_u = bonus_data[0]
    if current_rtp < 89 and top_u > 1.2:
        st.success(f"🔥 ATTACCO: Bonus {top_b} in scadenza + RTP favorevole.")
    else:
        st.info("⚖️ ATTESA: Sistema in equilibrio. Gioca frazioni minime.")
    st.markdown('</div>', unsafe_allow_html=True)

# SIDEBAR CONTROLLI
st.sidebar.markdown("### 🛠️ Tool Pro")
if st.sidebar.button("⏪ Annulla Ultimo", use_container_width=True):
    if st.session_state.history:
        st.session_state.history.pop(0)
        st.session_state.total_spins -= 1
        st.rerun()

if st.sidebar.button("👤 Cambio Dealer", use_container_width=True):
    st.session_state.dealer_spins = 0
    st.session_state.dealer_history = []
    st.rerun()

if st.sidebar.button("🗑️ Reset Sessione", use_container_width=True):
    st.session_state.history = []; st.session_state.total_spins = 0; st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(" Designed for Mobile Oracle Pro")

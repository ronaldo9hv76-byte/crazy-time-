import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter
import math

# Configurazione Pagina - Tema Scuro Nativo e Sidebar espansa
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

    /* Colori diversi per sezioni per distinzione immediata */
    .section-motore { border-left: 5px solid #0A84FF; background: rgba(10, 132, 255, 0.05); }
    .section-markov { border-left: 5px solid #BF5AF2; background: rgba(191, 90, 242, 0.05); }
    .section-bonus { border-left: 5px solid #FF9F0A; background: rgba(255, 159, 10, 0.05); }
    .section-tattica { border-radius: 15px; padding: 15px; border: 1px solid #32D74B; background: rgba(50, 215, 75, 0.05); }

    /* Bottoni stile Apple Pro */
    .stButton>button {
        border-radius: 12px;
        background-color: #1C1C1E;
        color: white;
        border: 1px solid #3A3A3C;
        padding: 10px 20px;
        transition: all 0.2s ease-in-out;
        font-weight: 500;
    }
    .stButton>button:hover {
        border-color: #0A84FF;
        background-color: #2C2C2E;
        transform: scale(1.02);
    }
    
    /* Sidebar scura e compatta */
    [data-testid="stSidebar"] {
        background-color: #161617;
        border-right: 1px solid #3A3A3C;
    }
    
    /* Progress bar personalizzata */
    .stProgress > div > div > div > div {
        background-color: #BF5AF2;
    }

    h1, h2, h3 {
        font-family: "SF Pro Display", "Helvetica Neue", sans-serif;
        letter-spacing: -0.5px;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

# --- COSTANTI RUOTA ---
SEGMENTS = ['1', '2', '5', '10', 'Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
BONUS_LIST = ['Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']

EXPECTED_FREQ = {
    '1': 21/54, '2': 13/54, '5': 7/54, '10': 4/54,
    'Coin Flip': 4/54, 'Pachinko': 2/54, 'Cash Hunt': 2/54, 'Crazy Time': 1/54
}

NEIGHBORS = {
    '1': ['10', '2', '5', 'Coin Flip'],
    '2': ['1', '10', 'Crazy Time', '5'],
    '5': ['1', 'Pachinko', '2', 'Cash Hunt'],
    '10': ['1', '2', 'Coin Flip', 'Cash Hunt'],
    'Coin Flip': ['1', '10', '2', '5'],
    'Pachinko': ['5', '1', 'Crazy Time'],
    'Cash Hunt': ['10', '5', '1'],
    'Crazy Time': ['1', '5', 'Pachinko']
}

CORRELATION_MAP = {
    '5': ['Pachinko', 'Cash Hunt'],
    '10': ['Coin Flip', 'Cash Hunt'],
    '2': ['Crazy Time', 'Coin Flip'],
    '1': ['Coin Flip', 'Pachinko']
}

# --- SESSION STATE ---
if 'history' not in st.session_state: st.session_state.history = []
if 'total_spins' not in st.session_state: st.session_state.total_spins = 0
if 'dealer_spins' not in st.session_state: st.session_state.dealer_spins = 0
if 'dealer_history' not in st.session_state: st.session_state.dealer_history = []

# --- FUNZIONI CORE ---
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

def get_chi_square(h, window=40):
    recent = h[:window] if len(h) >= window else h
    if len(recent) < 15: return None
    n = len(recent)
    counts = Counter(recent)
    return sum((counts.get(seg, 0) - EXPECTED_FREQ[seg] * n) ** 2 / (EXPECTED_FREQ[seg] * n) for seg in SEGMENTS)

def get_composite_score(h, seg, markov_prob):
    if not h: return 0.0
    sfas = get_sfasamento(h, seg)
    exp_gap = 1 / EXPECTED_FREQ.get(seg, 0.1)
    sfas_score = min(sfas / exp_gap, 2.0) / 2.0
    return (0.50 * markov_prob + 0.50 * sfas_score)

# --- INTERFACCIA PRINCIPALE ---
st.title(" CT Oracle Pro v2")

# BARRA SUPERIORE METRICHE
m1, m2, m3, m4, m5 = st.columns(5)
with m1: current_rtp = st.number_input("RTP Live %", value=96.0, step=0.1)
m2.metric("Giri Totali", st.session_state.total_spins)
m3.metric("Giri Dealer", st.session_state.dealer_spins)
sfas_gen = get_sfasamento(st.session_state.history) if st.session_state.history else 0
m4.metric("Sfas. Bonus", sfas_gen)
chi2 = get_chi_square(st.session_state.history)
if chi2 is not None:
    m5.metric("Chi2 Bias", f"{chi2:.1f}", delta="BIAS" if chi2 > 14.07 else "RANDOM")

st.markdown("---")

# TASTIERA INPUT (Layout Apple Pro)
st.markdown("### ⌨️ Inserimento Rapido")
cols_btn = st.columns(8)
for idx, seg in enumerate(SEGMENTS):
    if cols_btn[idx].button(seg, use_container_width=True):
        st.session_state.history.insert(0, seg)
        st.session_state.dealer_history.insert(0, seg)
        st.session_state.total_spins += 1
        st.session_state.dealer_spins += 1
        st.rerun()

# NASTRO STORICO ORIZZONTALE
if st.session_state.history:
    recent20 = st.session_state.history[:20]
    st.markdown('<div style="display: flex; overflow-x: auto; padding-bottom: 15px;">' + "".join([
        f'<div style="background:{"#FF3B30" if is_bonus(v) else "#1C1C1E"}; border: 1px solid #3A3A3C; border-radius:10px; padding:8px 15px; margin-right:8px; font-weight:600; min-width:80px; text-align:center; color:white;">{v[:4] if is_bonus(v) else v}</div>' for v in recent20
    ]) + '</div>', unsafe_allow_html=True)

st.markdown("---")

# GRIGLIA DI ANALISI (MOTORE - MARKOV - BONUS)
if len(st.session_state.history) > 5:
    h = st.session_state.history
    markov, ent_total, ent_recent = get_analysis_weighted(h)
    last = h[0]

    col1, col2, col3 = st.columns([1, 1.2, 1.3])

    with col1:
        st.markdown('<div class="metric-container section-motore">', unsafe_allow_html=True)
        st.subheader("📡 Motore Live")
        st.metric("Entropia (15g)", f"{ent_recent:.2f}")
        if ent_recent < 1.85: st.success("STATO: PUNTUALE")
        elif ent_recent < 2.2: st.warning("STATO: INTERMEDIO")
        else: st.error("STATO: CAOTICO")
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
            st.markdown(f"""
                <div style='display:flex; justify-content:space-between; margin-bottom:5px;'>
                    <span style='color:{color}; font-weight:bold;'>{b}</span>
                    <span>Gap: {s} | <b style='color:{color}'>{u:.1f}x</b></span>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # SEZIONE TATTICA FINALE
    st.markdown('<div class="section-tattica">', unsafe_allow_html=True)
    st.subheader("📋 Piano d'Azione Strategico")
    top_b, top_s, top_u = bonus_data[0]
    if current_rtp < 90 and top_u > 1.3:
        st.success(f"🔥 SEGNALE FORTE: Il banco è sotto RTP e {top_b} è in altissima urgenza (Gap {top_s}). Attacco consigliato.")
    elif ent_recent > 2.3:
        st.error("⚠️ CAUTELA: Entropia troppo alta. Il dealer sta rompendo i pattern. Gioca solo coperture minime.")
    else:
        st.info("⚖️ ATTESA: Sistema in fase di bilanciamento. Segui Markov sui numeri bassi (1-2).")
    st.markdown('</div>', unsafe_allow_html=True)

# SIDEBAR CONTROLLI (Design Integrato)
st.sidebar.markdown("### 🛠️ Pannello Pro")
st.sidebar.markdown("---")

if st.sidebar.button("⏪ Annulla Ultimo", use_container_width=True):
    if st.session_state.history:
        st.session_state.history.pop(0)
        st.session_state.total_spins = max(0, st.session_state.total_spins - 1)
        if st.session_state.dealer_history:
            st.session_state.dealer_history.pop(0)
            st.session_state.dealer_spins = max(0, st.session_state.dealer_spins - 1)
        st.rerun()

if st.sidebar.button("👤 Cambio Dealer", use_container_width=True):
    st.session_state.dealer_spins = 0
    st.session_state.dealer_history = []
    st.sidebar.success("Dealer Resettato!")
    st.rerun()

if st.sidebar.button("🗑️ Reset Sessione", use_container_width=True):
    st.session_state.history = []
    st.session_state.dealer_history = []
    st.session_state.total_spins = 0
    st.session_state.dealer_spins = 0
    st.rerun()

st.sidebar.markdown("---")
# Visualizzazione rapida Gap nella Sidebar
if st.session_state.history:
    st.sidebar.write("**📈 Riepilogo Gap Bonus:**")
    for b, s, u in bonus_data:
        color = "🔴" if u > 1.8 else "🟡" if u > 1.0 else "🟢"
        st.sidebar.write(f"{color} {b}: **{s}**")

st.sidebar.caption(" CT Oracle Pro v2 | 2026 Edition")

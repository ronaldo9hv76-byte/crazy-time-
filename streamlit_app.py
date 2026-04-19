import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter
import math

# --- CONFIGURAZIONE PAGINA APPLE STYLE ---
st.set_page_config(page_title='CT Oracle Pro v4', layout='wide', initial_sidebar_state='expanded')

st.markdown("""
    <style>
    /* Apple Dark Mode Theme */
    .stApp { background-color: #000000; color: #F5F5F7; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif; }
    .glass-box {
        background: rgba(28, 28, 30, 0.65);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 12px;
    }
    .action-box {
        background: linear-gradient(145deg, #1C1C1E 0%, #2C2C2E 100%);
        border-radius: 20px; padding: 25px; border: 1px solid #3A3A3C;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    .stButton>button {
        border-radius: 12px; background-color: #1C1C1E; color: white;
        border: 1px solid #3A3A3C; transition: all 0.2s ease; font-weight: 600;
    }
    .stButton>button:hover {
        border-color: #0A84FF; background-color: #2C2C2E; transform: scale(1.02);
    }
    [data-testid="stSidebar"] { background-color: #161617; border-right: 1px solid #2C2C2E; }
    h1, h2, h3, h4 { letter-spacing: -0.5px; font-weight: 700; }
    /* Colori Semaforo */
    .text-green { color: #32D74B; } .text-orange { color: #FF9F0A; } .text-red { color: #FF3B30; } .text-blue { color: #0A84FF; }
    </style>
""", unsafe_allow_html=True)

# --- COSTANTI DI GIOCO ---
SEGMENTS = ['1', '2', '5', '10', 'Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
BONUS_LIST = ['Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
EXPECTED_FREQ = {'1': 21/54, '2': 13/54, '5': 7/54, '10': 4/54, 'Coin Flip': 4/54, 'Pachinko': 2/54, 'Cash Hunt': 2/54, 'Crazy Time': 1/54}
# Stima payout per calcolo Local RTP (Ritorno per Unità scommessa)
ESTIMATED_PAYOUTS = {'1': 2, '2': 3, '5': 6, '10': 11, 'Coin Flip': 15, 'Pachinko': 25, 'Cash Hunt': 25, 'Crazy Time': 50}

NEIGHBORS = {
    '1': ['10', '2', '5', 'Coin Flip'], '2': ['1', '10', 'Crazy Time', '5'],
    '5': ['1', 'Pachinko', '2', 'Cash Hunt'], '10': ['1', '2', 'Coin Flip', 'Cash Hunt'],
    'Coin Flip': ['1', '10', '2', '5'], 'Pachinko': ['5', '1', 'Crazy Time'],
    'Cash Hunt': ['10', '5', '1'], 'Crazy Time': ['1', '5', 'Pachinko']
}
CORRELATION_MAP = {'5': ['Pachinko', 'Cash Hunt'], '10': ['Coin Flip', 'Cash Hunt'], '2': ['Crazy Time', 'Coin Flip'], '1': ['Coin Flip', 'Pachinko']}

# --- INIT STATE ---
for key in ['history', 'dealer_history']:
    if key not in st.session_state: st.session_state[key] = []
for key in ['total_spins', 'dealer_spins']:
    if key not in st.session_state: st.session_state[key] = 0

# --- CORE MATH ENGINE ---
def is_bonus(o): return o in BONUS_LIST

def get_sfasamento(h, target=None):
    for i, val in enumerate(h):
        if target:
            if val == target: return i
        elif is_bonus(val): return i
    return len(h)

def entropy(data):
    if not data: return 0.0
    c = Counter(data)
    probs = [v / len(data) for v in c.values()]
    return -sum(p * math.log2(p) for p in probs if p > 0)

def get_analysis_weighted(h):
    matrix = pd.DataFrame(0.0, index=SEGMENTS, columns=SEGMENTS)
    n = len(h)
    ent_recent = entropy(h[:15])
    
    # DECADIMENTO ADATTIVO (Nuova Implementazione)
    decay_factor = 0.07 # Standard
    if ent_recent > 2.2: decay_factor = 0.15 # Dealer caotico, dimentica in fretta
    elif ent_recent < 1.85: decay_factor = 0.03 # Dealer costante, memoria lunga
    
    for i in range(n - 1, 0, -1):
        age = n - 1 - i
        weight = math.exp(-decay_factor * age)
        matrix.loc[h[i], h[i - 1]] += weight
        
    m_norm = matrix.div(matrix.sum(axis=1).replace(0, 1), axis=0)
    return m_norm, entropy(h), ent_recent

def get_local_rtp(h):
    # CALCOLO RTP DELLA TUA SESSIONE
    if not h: return 100.0
    total_won = sum(ESTIMATED_PAYOUTS.get(x, 0) for x in h)
    total_bet = len(h) * 8 # Simulando la copertura di tutti gli 8 spot
    return (total_won / total_bet) * 100

def get_hot_cold(h, window=20):
    recent = h[:window] if len(h) >= window else h
    if not recent: return {}, {}
    n = len(recent); counts = Counter(recent)
    hot, cold = {}, {}
    for seg in SEGMENTS:
        dev = (counts.get(seg, 0) / n - EXPECTED_FREQ[seg]) / EXPECTED_FREQ[seg]
        if dev > 0.30: hot[seg] = dev
        elif dev < -0.30: cold[seg] = dev
    return hot, cold

def get_chi_square(h, window=40):
    recent = h[:window] if len(h) >= window else h
    if len(recent) < 15: return None
    n = len(recent); counts = Counter(recent)
    return sum((counts.get(seg, 0) - EXPECTED_FREQ[seg] * n) ** 2 / (EXPECTED_FREQ[seg] * n) for seg in SEGMENTS)

def get_composite_score(h, seg, markov_prob):
    if not h: return 0.0
    sfas = get_sfasamento(h, seg)
    exp_gap = 1 / EXPECTED_FREQ.get(seg, 0.1)
    sfas_score = min(sfas / exp_gap, 2.0) / 2.0
    return (0.45 * markov_prob + 0.55 * sfas_score)

def detect_pattern(h, length=3):
    if len(h) < length * 2 + 1: return None
    recent = tuple(h[:length])
    for i in range(length, len(h) - length):
        if tuple(h[i:i + length]) == recent: return h[i - 1] if i > 0 else None
    return None

def get_global_confidence(ent_recent, chi2, n_spins):
    score = 50.0
    if ent_recent < 1.8: score += 20
    elif ent_recent >= 2.2: score -= 20
    if chi2 is not None:
        if chi2 > 18.48: score += 20
        elif chi2 > 14.07: score += 10
    if n_spins < 10: score -= 25
    return max(0, min(100, int(score)))

def get_bet_sizing(confidence):
    # BET SIZING DINAMICO (Nuova Implementazione)
    if confidence >= 80: return "💰 3 UNITÀ (Puntata Piena)"
    if confidence >= 55: return "💵 2 UNITÀ (Puntata Media)"
    if confidence >= 35: return "🪙 1 UNITÀ (Copertura Minima)"
    return "🚫 NO BET (Rischio Eccessivo)"

def get_next_bet(h, markov, last, ent_recent, chi2, local_rtp, confidence):
    if local_rtp > 130:
        return ('STOP / ATTESA', None, [], 'RTP Locale Altissimo: Il banco sta strizzando le probabilità.', 'BASSA')
    if ent_recent > 2.5:
        return ('SALTA IL GIRO', None, [], 'Motore nel Caos Totale. Impossibile tracciare pattern.', 'BASSA')

    bonus_data = [(b, get_sfasamento(h, b), get_sfasamento(h, b) / (1 / EXPECTED_FREQ[b])) for b in BONUS_LIST]
    bonus_data.sort(key=lambda x: x[2], reverse=True)
    top_bonus, top_sfas, top_urgency = bonus_data[0]
    
    preds = markov.loc[last].sort_values(ascending=False)
    markov_fav = preds.index[0] if preds.iloc[0] > 0 else None
    corr_bonus = CORRELATION_MAP.get(markov_fav, []) if markov_fav else []

    if top_urgency > 2.0 and ent_recent < 2.1:
        mot = f"{top_bonus} in sfasamento critico ({top_sfas} giri). Motore stabile."
        return ('ATTACCO DIRETTO BONUS', markov_fav, [top_bonus] + [b for b in corr_bonus if b != top_bonus], mot, 'ALTISSIMA')
    if local_rtp < 85 and top_urgency > 1.3:
        mot = f"RTP Locale bassissimo ({local_rtp:.0f}%). Il banco deve pagare. Punta {markov_fav} e settori."
        return ('ATTACCO SETTORE', markov_fav, corr_bonus, mot, 'ALTA')
    if top_urgency > 1.5:
        return ('COPERTURA SELETTIVA', markov_fav, [top_bonus], f"{top_bonus} in pressione. Usa puntate minime.", 'MEDIA')
    
    return ('MONITORAGGIO', markov_fav, [], "Nessun segnale di rottura statistica imminente.", 'BASSA')


# --- UI: DASHBOARD ---
st.title(" CT Oracle Pro v4")

t1, t2, t3, t4, t5 = st.columns(5)
local_rtp_val = get_local_rtp(st.session_state.history)
t1.metric("Local RTP (Tua Sessione)", f"{local_rtp_val:.1f}%", delta="Sotto Media" if local_rtp_val < 90 else "Sopra Media", delta_color="inverse")
t2.metric("Giri Totali", st.session_state.total_spins)
t3.metric("Giri Dealer", st.session_state.dealer_spins)
t4.metric("Sfas. Bonus Gen.", get_sfasamento(st.session_state.history))
chi2_val = get_chi_square(st.session_state.history)
t5.metric("Chi2 Bias", f"{chi2_val:.1f}" if chi2_val else "N/A", delta="BIAS RILEVATO" if chi2_val and chi2_val > 14.07 else "Random", delta_color="off" if chi2_val and chi2_val > 14.07 else "normal")

# INPUT TASTIERA
st.markdown("### ⌨️ Input Rapido")
cols_btn = st.columns(8)
for idx, seg in enumerate(SEGMENTS):
    if cols_btn[idx].button(seg, use_container_width=True):
        st.session_state.history.insert(0, seg)
        st.session_state.dealer_history.insert(0, seg)
        st.session_state.total_spins += 1
        st.session_state.dealer_spins += 1
        st.rerun()

# NASTRO CRONOLOGICO
if st.session_state.history:
    recent = st.session_state.history[:20]
    st.markdown('<div style="display:flex; overflow-x:auto; padding-bottom:10px;">' + "".join([
        f'<div style="background:{"#FF3B30" if is_bonus(v) else "#2C2C2E"}; border-radius:8px; padding:6px 14px; margin-right:6px; font-weight:700; color:white; min-width:60px; text-align:center;">{v[:4] if is_bonus(v) else v}</div>' for v in recent
    ]) + '</div>', unsafe_allow_html=True)

st.markdown("---")

# MOTORE PRINCIPALE
if len(st.session_state.history) > 5:
    h = st.session_state.history
    markov, ent_total, ent_recent = get_analysis_weighted(h)
    last = h[0]
    confidence = get_global_confidence(ent_recent, chi2_val, len(h))
    
    # ELABORAZIONE DECISIONE
    azione, target_num, target_bonus_list, motivo, urgenza = get_next_bet(h, markov, last, ent_recent, chi2_val, local_rtp_val, confidence)

    # --- ACTION BOX (DECISORE FINALE) ---
    box_color = "linear-gradient(145deg, #4A1942 0%, #2A0845 100%)" if urgenza == 'ALTISSIMA' else \
                "linear-gradient(145deg, #1A472A 0%, #0F2A1A 100%)" if urgenza == 'ALTA' else \
                "linear-gradient(145deg, #1C1C1E 0%, #2C2C2E 100%)"
    
    st.markdown(f"""
        <div class="action-box" style="background: {box_color};">
            <h4 style="color:#ffffff99; margin:0; text-transform:uppercase; font-size:12px;">Comando Tattico</h4>
            <h2 style="color:white; margin:5px 0 10px 0; font-size:32px;">{azione}</h2>
            <p style="color:#ffffffcc; font-size:16px; margin:0 0 15px 0;">{motivo}</p>
            <div style="display:flex; gap:20px;">
                <div style="background:rgba(0,0,0,0.3); padding:10px 15px; border-radius:10px;">
                    <span style="color:#ffffff99; font-size:12px;">Puntata Consigliata</span><br>
                    <b style="color:#32D74B; font-size:16px;">{get_bet_sizing(confidence)}</b>
                </div>
                <div style="background:rgba(0,0,0,0.3); padding:10px 15px; border-radius:10px;">
                    <span style="color:#ffffff99; font-size:12px;">Confidenza Sistema</span><br>
                    <b style="color:white; font-size:16px;">{confidence}%</b>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # BLOCCO COPERTURE SPECIFICHE
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="glass-box">', unsafe_allow_html=True)
        st.markdown("#### 🎯 Numero da Coprire")
        if target_num:
            st.markdown(f"<h1 class='text-green' style='text-align:center;'>{target_num}</h1>", unsafe_allow_html=True)
            st.caption(f"Vicini fisici: {', '.join(NEIGHBORS.get(target_num, [])[:2])}")
        else:
            st.info("Nessun numero specifico suggerito.")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with c2:
        st.markdown('<div class="glass-box">', unsafe_allow_html=True)
        st.markdown("#### 🚀 Bonus Prioritari")
        if target_bonus_list:
            for tb in target_bonus_list[:2]:
                s = get_sfasamento(h, tb)
                exp = round(1 / EXPECTED_FREQ[tb])
                st.markdown(f"<h3 class='text-orange' style='margin:0;'>{tb} <span style='font-size:14px; color:white;'>(Gap: {s}/{exp})</span></h3>", unsafe_allow_html=True)
        else:
            st.info("Nessun bonus in urgenza critica.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    
    # GRIGLIA ANALISI TECNICA (Motore, Trend, Dettagli)
    colA, colB, colC = st.columns([1, 1, 1.2])
    
    with colA:
        st.markdown('<div class="glass-box">', unsafe_allow_html=True)
        st.markdown("#### 📡 Telemetria Motore")
        st.metric("Entropia Attuale", f"{ent_recent:.2f}")
        
        # GRAFICO TREND ENTROPIA RECENTE
        if len(h) >= 15:
            ent_trend = [entropy(h[i:i+10]) for i in range(10)]
            ent_trend.reverse()
            st.caption("Trend Entropia (Ultime 10 rilevazioni)")
            st.line_chart(pd.DataFrame(ent_trend, columns=["Caos"]), height=100)
            
        st.markdown('</div>', unsafe_allow_html=True)

    with colB:
        st.markdown('<div class="glass-box">', unsafe_allow_html=True)
        st.markdown("#### 🔮 Top 3 Markov")
        preds = markov.loc[last].sort_values(ascending=False).head(3)
        for val, prob in preds.items():
            if prob > 0:
                sc = get_composite_score(h, val, prob)
                st.write(f"**{val}** (Score: {sc:.2f})")
                st.progress(float(prob))
        st.markdown('</div>', unsafe_allow_html=True)

    with colC:
        st.markdown('<div class="glass-box">', unsafe_allow_html=True)
        st.markdown("#### 📊 Dettaglio Sfasamento")
        for b in BONUS_LIST:
            s = get_sfasamento(h, b)
            urg = s / (1 / EXPECTED_FREQ[b])
            color = "#FF3B30" if urg > 1.8 else "#FF9F0A" if urg > 1.0 else "#32D74B"
            st.markdown(f"<div style='display:flex; justify-content:space-between; border-bottom:1px solid #3A3A3C; padding:5px 0;'><span style='color:{color}; font-weight:600;'>{b}</span> <span>{s} giri <b style='color:{color}'>({urg:.1f}x)</b></span></div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- SIDEBAR (CONTROLLI) ---
st.sidebar.markdown("## ⚙️ Controlli")
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
    st.sidebar.success("✅ Dealer Azzerato")
    st.rerun()

if st.sidebar.button("🗑️ Full Reset", use_container_width=True):
    st.session_state.history = []
    st.session_state.dealer_history = []
    st.session_state.total_spins = 0
    st.session_state.dealer_spins = 0
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(" CT Oracle Pro v4 | Terminale Quantitativo Definitivo")

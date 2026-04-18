import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter

st.set_page_config(page_title="CT Oracle Pro: Ultimate Edition", layout="wide")

# --- DATABASE FISICO DELLA RUOTA (Radar di Settore) ---
# Mappatura dei vicini fisici basata sulla disposizione standard della ruota
NEIGHBORS = {
    '1': ['10', '2', '5', 'Coin Flip'], # I '1' sono ovunque, qui mettiamo i vicini più comuni
    '2': ['1', '10', 'Crazy Time', '5'],
    '5': ['1', 'Pachinko', '2', 'Cash Hunt'],
    '10': ['1', '2', 'Coin Flip', 'Cash Hunt'],
    'Coin Flip': ['1', '10', '2', '5'],
    'Pachinko': ['5', '1', 'Crazy Time'],
    'Cash Hunt': ['10', '5', '1'],
    'Crazy Time': ['1', '5', 'Pachinko']
}

# Correlazione Strategica (Numero -> Bonus adiacente per Attacco)
CORRELATION_MAP = {
    '5': ['Pachinko', 'Cash Hunt'],
    '10': ['Coin Flip', 'Cash Hunt'],
    '2': ['Crazy Time', 'Coin Flip'],
    '1': ['Coin Flip', 'Pachinko']
}

if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'total_spins' not in st.session_state:
    st.session_state['total_spins'] = 0
if 'dealer_spins' not in st.session_state:
    st.session_state['dealer_spins'] = 0

SEGMENTS = ['1', '2', '5', '10', 'Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
BONUS_LIST = ['Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']

# --- FUNZIONI LOGICHE ---
def is_bonus(outcome):
    return outcome in BONUS_LIST

def get_sfasamento(h, target=None):
    for i, val in enumerate(h):
        if target:
            if val == target: return i
        else:
            if is_bonus(val): return i
    return len(h)

def get_analysis_weighted(h):
    """Calcolo Markov con PESO TEMPORALE (Decay Factor)"""
    matrix = pd.DataFrame(0.0, index=SEGMENTS, columns=SEGMENTS)
    
    # Più il numero è recente (i piccolo), più il peso è alto
    for i in range(len(h)-1, 0, -1):
        # i va dal più vecchio al più recente
        # Peso inversamente proporzionale alla distanza temporale
        weight = 1.0 / i 
        matrix.loc[h[i], h[i-1]] += weight
    
    m_norm = matrix.div(matrix.sum(axis=1).replace(0, 1), axis=0)
    
    def entropy(data):
        c = Counter(data)
        probs = [v/len(data) for v in c.values()]
        return -sum(p * np.log2(p) for p in probs if p > 0)
    
    return m_norm, entropy(h), entropy(h[:15])

# --- INTERFACCIA ---
st.title("🎯 CT Oracle Pro: Ultimate Markov & Sector Radar")

top1, top2, top3, top4 = st.columns(4)
current_rtp = top1.number_input("RTP Live (%)", min_value=0.0, value=96.0)
top2.metric("Giri Totali", st.session_state.total_spins)
top3.metric("Giri Dealer", st.session_state.dealer_spins)
sfas_gen = get_sfasamento(st.session_state.history) if st.session_state.history else 0
top4.metric("Sfasamento Bonus", sfas_gen)

st.markdown("---")

# Tastiera Input
st.write("### ⌨️ Inserimento Rapido")
c = st.columns(8)
for i, s in enumerate(SEGMENTS):
    if c[i].button(s, use_container_width=True):
        st.session_state.history.insert(0, s)
        st.session_state.total_spins += 1
        st.session_state.dealer_spins += 1
        st.rerun()

# --- MOTORE DI ANALISI ---
if len(st.session_state.history) > 5:
    h = st.session_state.history
    markov, ent_total, ent_recent = get_analysis_weighted(h)
    last = h[0]
    
    col1, col2, col3 = st.columns([1, 1, 1.5])
    
    with col1:
        st.subheader("📡 Stato Motore")
        st.metric("Ultimo", last)
        st.metric("Entropia Recente", f"{ent_recent:.2f}")
        if ent_recent < 1.85: st.success("PUNTUALE: Motore Predictable")
        else: st.warning("CAOTICO: Rumore Bianco")

    with col2:
        st.subheader("🔮 Markov Pesato")
        preds = markov.loc[last].sort_values(ascending=False).head(3)
        markov_fav = preds.index[0] if not preds.empty and preds.iloc[0] > 0 else None
        
        for i, (val, prob) in enumerate(preds.items()):
            if prob > 0:
                st.write(f"**{val}** (Affidabilità: {prob:.1%})")
                # Visualizza i vicini fisici del favorito
                vicini = NEIGHBORS.get(val, [])
                st.caption(f"↳ Vicini ruota: {', '.join(vicini)}")

    with col3:
        st.subheader("🎯 Radar Settore & Bonus")
        if markov_fav in CORRELATION_MAP:
            target_bonus = CORRELATION_MAP[markov_fav]
            for tb in target_bonus:
                sfasa_tb = get_sfasamento(h, tb)
                if sfasa_tb > 12:
                    st.error(f"🔥 ATTACCO: {tb} (Sfasamento: {sfasa_tb})")
                    st.write(f"Correlato al favorito Markov: {markov_fav}")
                else:
                    st.info(f"Monitor: {tb} (Sfasamento: {sfasa_tb})")

    st.markdown("---")
    
    # TATTICA AUTOMATICA
    st.subheader("📋 Manuale di Giocata")
    if current_rtp < 89 and ent_recent < 1.9:
        st.success(f"STRATEGIA: **ATTACCO AL SETTORE**. Markov chiama {markov_fav}. Copri il numero e i bonus correlati.")
    elif current_rtp > 115:
        st.error("STRATEGIA: **RECUPERO BANCO**. RTP alto, non forzare i bonus. Gioca solo per mantenimento (1-2).")
    else:
        st.info("STRATEGIA: **ATTESA STATISTICA**. Entra quando lo sfasamento supera i 10 giri.")

# Side Bar per gestione
st.sidebar.button("⏪ Cancella Ultimo", on_click=lambda: st.session_state.history.pop(0) if st.session_state.history else None)
st.sidebar.button("👤 Cambio Dealer", on_click=lambda: setattr(st.session_state, 'dealer_spins', 0))
st.sidebar.button("🗑️ Reset Totale", on_click=lambda: (st.session_state.history.clear(), setattr(st.session_state, 'total_spins', 0), setattr(st.session_state, 'dealer_spins', 0)))

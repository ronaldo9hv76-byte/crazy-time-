import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter

st.set_page_config(page_title="CT Oracle Pro", layout="wide")

# --- INIZIALIZZAZIONE SESSION STATE ---
if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'total_spins' not in st.session_state:
    st.session_state['total_spins'] = 0
if 'dealer_spins' not in st.session_state:
    st.session_state['dealer_spins'] = 0

SEGMENTS = ['1', '2', '5', '10', 'Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
BONUS_LIST = ['Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']

# --- FUNZIONI DI SUPPORTO ---
def is_bonus(outcome):
    return outcome in BONUS_LIST

def get_sfasamento(h):
    """Calcola da quanti giri non esce un bonus (h[0] è il più recente)"""
    for i, val in enumerate(h):
        if is_bonus(val):
            return i
    return len(h)

# --- CALCOLO MARKOV PURO (Tuo codice originale ottimizzato) ---
def get_analysis(h):
    # Matrice di transizione
    matrix = pd.DataFrame(0.0, index=SEGMENTS, columns=SEGMENTS)
    for i in range(len(h)-1, 0, -1):
        # h[i] è il precedente, h[i-1] è il successivo cronologicamente
        matrix.loc[h[i], h[i-1]] += 1
    
    m_norm = matrix.div(matrix.sum(axis=1).replace(0, 1), axis=0)
    
    # Entropia di Shannon
    def entropy(data):
        c = Counter(data)
        probs = [v/len(data) for v in c.values()]
        return -sum(p * np.log2(p) for p in probs if p > 0)
    
    return m_norm, entropy(h), entropy(h[:20])

# --- UI PRINCIPALE ---
st.title("🎯 CT Oracle Pro: Markov & RTP Engine")

# Pannello Superiore: Contatori e RTP
top1, top2, top3, top4 = st.columns(4)
current_rtp = top1.number_input("RTP Ultime 100 Giocate (%)", min_value=0.0, max_value=500.0, value=96.0, step=0.1)
top2.metric("Giri Totali Sessione", st.session_state.total_spins)
top3.metric("Giri Dealer Attuale", st.session_state.dealer_spins)
sfasamento_attuale = get_sfasamento(st.session_state.history) if st.session_state.history else 0
top4.metric("Sfasamento (Giri da ultimo Bonus)", sfasamento_attuale)

st.markdown("---")

# Input rapido (Tastiera)
st.write("### ⌨️ Inserimento Uscite")
c = st.columns(8)
for i, s in enumerate(SEGMENTS):
    if c[i].button(s, use_container_width=True):
        st.session_state.history.insert(0, s)
        st.session_state.total_spins += 1
        st.session_state.dealer_spins += 1
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# Pulsanti di Gestione
ctrl1, ctrl2, ctrl3 = st.columns(3)
if ctrl1.button("⏪ Annulla Ultimo Inserimento", use_container_width=True):
    if st.session_state.history:
        st.session_state.history.pop(0)
        st.session_state.total_spins = max(0, st.session_state.total_spins - 1)
        st.session_state.dealer_spins = max(0, st.session_state.dealer_spins - 1)
        st.rerun()

if ctrl2.button("👤 Cambio Dealer (Reset parziale)", use_container_width=True):
    st.session_state.dealer_spins = 0
    st.rerun()

if ctrl3.button("🗑️ Reset Totale Sessione", type="primary", use_container_width=True):
    st.session_state.history.clear()
    st.session_state.total_spins = 0
    st.session_state.dealer_spins = 0
    st.rerun()

st.markdown("---")

# --- ANALISI E STRATEGIA ---
if len(st.session_state.history) > 5:
    h = st.session_state.history
    markov, ent_total, ent_recent = get_analysis(h)
    last = h[0]
    
    # Dashboard Strategica
    col1, col2, col3 = st.columns([1, 1, 1.5])
    
    with col1:
        st.subheader("Stato Motore")
        st.metric("Ultimo Uscito", last)
        diff = ent_recent - ent_total
        st.metric("Drift Entropia (Ultime 20)", f"{ent_recent:.2f}", f"{diff:.2f}", delta_color="inverse")
        
        if ent_recent < 1.8:
            st.success("🔥 Motore Bloccato. Prevedibilità alta.")
        elif ent_recent < 2.2:
            st.info("⚡ Varianza media. Flusso regolare.")
        else:
            st.warning("🎲 Caos totale. Dealer in ritaratura.")

    with col2:
        st.subheader("Radar Markov (Next Spin)")
        preds = markov.loc[last].sort_values(ascending=False).head(3)
        markov_fav = preds.index[0] if not preds.empty and preds.iloc[0] > 0 else None
        
        for i, (val, prob) in enumerate(preds.items()):
            if prob > 0:
                st.write(f"{i+1}️° Favorito: **{val}** ({prob:.1%})")

    with col3:
        st.subheader("🎯 Tattica Operativa (Semaforo)")
        
        # LOGICA DEL SEMAFORO INTEGRATA
        if markov_fav:
            if current_rtp < 88.0:
                if ent_recent < 1.85 and markov_fav in ['5', '10'] and sfasamento_attuale >= 8:
                    st.success(f"🟢 **ATTACCO AL BONUS**\nPunta {markov_fav} e copri il Bonus adiacente. Sfasamento maturo.")
                elif ent_recent > 2.10:
                    st.info("🟢 **ATTESA**\nRTP favorevole ma ruota troppo instabile. Attendi.")
                else:
                    st.info("🟢 **SETUP**\nTraccia i numeri in attesa dell'allineamento di Markov.")
                    
            elif 90.0 <= current_rtp <= 105.0:
                if ent_recent < 1.80 and sfasamento_attuale < 6:
                    st.warning(f"🟡 **MANUTENZIONE**\nGioca flat su {markov_fav}. Il banco è in equilibrio.")
                elif ent_recent < 1.80 and markov_fav == '2' and sfasamento_attuale > 12:
                    st.error("🟡 **ZONA ROSSA CRAZY TIME**\nPunta il 2 e copri CT per max 3 giri.")
                else:
                    st.warning("🟡 **ATTESA STANDARD**\nNessun vantaggio statistico chiaro.")
                    
            elif current_rtp > 115.0:
                if markov_fav == '10' and len(h) >= 2 and h[:2] == ['10', '10']:
                    st.error("🔴 **TRAPPOLA DEL BANCO**\nFingono il salto sul bonus. Non puntare.")
                elif ent_recent < 1.60 and markov_fav in ['1', '2']:
                    st.error(f"🔴 **DIFESA TOTALE**\nDivieto di puntare Bonus! Gioca solo {markov_fav} per mantenimento.")
                else:
                    st.error("🔴 **STOP LOSS**\nIl banco sta recuperando un passivo grave. Fermati.")
            else:
                st.write("⚪ Transizione in corso...")

    with st.expander("Visualizza Matrice di Transizione Completa"):
        st.dataframe(markov.style.format("{:.1%}"))
else:
    st.info("Inserisci almeno 6 risultati per attivare il motore Markov e la Tattica Operativa.")

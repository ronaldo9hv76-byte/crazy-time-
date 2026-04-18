import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter

st.set_page_config(page_title="CT Oracle Pro", layout="wide")

if 'history' not in st.session_state:
    st.session_state['history'] = []

# --- CALCOLO MARKOV PURO ---
def get_analysis(h):
    n = len(h)
    # Matrice di transizione
    matrix = pd.DataFrame(0.0, index=SEGMENTS, columns=SEGMENTS)
    for i in range(len(h)-1, 0, -1):
        matrix.loc[h[i], h[i-1]] += 1
    
    m_norm = matrix.div(matrix.sum(axis=1).replace(0, 1), axis=0)
    
    # Entropia di Shannon
    def entropy(data):
        c = Counter(data)
        probs = [v/len(data) for v in c.values()]
        return -sum(p * np.log2(p) for p in probs if p > 0)
    
    return m_norm, entropy(h), entropy(h[:20])

# --- UI ---
SEGMENTS = ['1', '2', '5', '10', 'Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
st.title("🎯 CT Oracle: Pure Markov Engine")

# Input rapido
c = st.columns(8)
for i, s in enumerate(SEGMENTS):
    if c[i].button(s):
        st.session_state.history.insert(0, s)
        st.rerun()

if len(st.session_state.history) > 5:
    h = st.session_state.history
    markov, ent_total, ent_recent = get_analysis(h)
    last = h[0]
    
    # Dashboard Strategica
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.metric("Ultimo Uscito", last)
        diff = ent_recent - ent_total
        st.metric("Drift Entropia", f"{ent_recent:.2f}", f"{diff:.2f}", delta_color="inverse")
        
        if ent_recent < 2.2:
            st.success("🔥 PATTERN IDENTIFICATO: Fase di bassa varianza. Fidati della matrice.")
        else:
            st.warning("🎲 RUMORE BIANCO: Il motore sta rimescolando. Prudenza.")

    with col2:
        st.subheader("Predizione Fisica (Prossimo Giro)")
        preds = markov.loc[last].sort_values(ascending=False).head(3)
        for i, (val, prob) in enumerate(preds.items()):
            if prob > 0:
                st.write(f"{i+1}️° Favorito: **{val}** (Prob. Statistica: {prob:.1%})")

    with st.expander("Visualizza Matrice di Transizione Completa"):
        st.dataframe(markov.style.format("{:.1%}"))
        
    if st.button("Annulla ultimo"):
        st.session_state.history.pop(0)
        st.rerun()

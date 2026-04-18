import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter
import math

# Configurazione Pagina
st.set_page_config(page_title="CT Oracle Pro v2", layout="wide")

# COSTANTI RUOTA (54 segmenti reali Crazy Time)
SEGMENTS = ['1', '2', '5', '10', 'Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']
BONUS_LIST = ['Coin Flip', 'Pachinko', 'Cash Hunt', 'Crazy Time']

# Frequenze teoriche basate sui 54 slot reali della ruota
EXPECTED_FREQ = {
    '1': 21/54,
    '2': 13/54,
    '5': 7/54,
    '10': 4/54,
    'Coin Flip': 4/54,
    'Pachinko': 2/54,
    'Cash Hunt': 2/54,
    'Crazy Time': 1/54,
}

# Vicini fisici sulla ruota (Radar di Settore)
NEIGHBORS = {
    '1': ['10', '2', '5', 'Coin Flip'],
    '2': ['1', '10', 'Crazy Time', '5'],
    '5': ['1', 'Pachinko', '2', 'Cash Hunt'],
    '10': ['1', '2', 'Coin Flip', 'Cash Hunt'],
    'Coin Flip': ['1', '10', '2', '5'],
    'Pachinko': ['5', '1', 'Crazy Time'],
    'Cash Hunt': ['10', '5', '1'],
    'Crazy Time': ['1', '5', 'Pachinko'],
}

# Bonus correlati al numero Markov favorito
CORRELATION_MAP = {
    '5': ['Pachinko', 'Cash Hunt'],
    '10': ['Coin Flip', 'Cash Hunt'],
    '2': ['Crazy Time', 'Coin Flip'],
    '1': ['Coin Flip', 'Pachinko'],
}

# SESSION STATE
for key, default in [
    ('history', []),
    ('total_spins', 0),
    ('dealer_spins', 0),
    ('dealer_history', []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# FUNZIONI CORE
def is_bonus(outcome):
    return outcome in BONUS_LIST

def get_sfasamento(h, target=None):
    for i, val in enumerate(h):
        if target:
            if val == target:
                return i
        else:
            if is_bonus(val):
                return i
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
        if not data:
            return 0.0
        c = Counter(data)
        probs = [v / len(data) for v in c.values()]
        return -sum(p * math.log2(p) for p in probs if p > 0)

    return m_norm, entropy(h), entropy(h[:15])

def get_hot_cold(h, window=20):
    recent = h[:window] if len(h) >= window else h
    if not recent:
        return {}, {}
    n = len(recent)
    counts = Counter(recent)
    hot, cold = {}, {}
    for seg in SEGMENTS:
        obs = counts.get(seg, 0) / n
        exp = EXPECTED_FREQ[seg]
        dev = (obs - exp) / exp
        if dev > 0.30:
            hot[seg] = dev
        elif dev < -0.30:
            cold[seg] = dev
    return hot, cold

def get_chi_square(h, window=40):
    recent = h[:window] if len(h) >= window else h
    if len(recent) < 15:
        return None
    n = len(recent)
    counts = Counter(recent)
    chi2_val = sum(
        (counts.get(seg, 0) - EXPECTED_FREQ[seg] * n) ** 2 / (EXPECTED_FREQ[seg] * n)
        for seg in SEGMENTS
    )
    return chi2_val

def get_trend(h, seg, short=10, long=25):
    if len(h) < long:
        return 0.0
    fs = h[:short].count(seg) / short
    fl = h[:long].count(seg) / long
    return (fs - fl) / fl if fl > 0 else 0.0

def get_composite_score(h, seg, markov_prob):
    if not h:
        return 0.0
    sfas = get_sfasamento(h, seg)
    exp_gap = 1 / EXPECTED_FREQ.get(seg, 0.1)
    sfas_score = min(sfas / exp_gap, 2.0) / 2.0
    trend = get_trend(h, seg)
    trend_score = max(0.0, min(trend + 0.5, 1.0))
    _, cold = get_hot_cold(h)
    cold_bonus = 0.2 if seg in cold else 0.0
    return (0.40 * markov_prob + 0.35 * sfas_score + 0.15 * trend_score + 0.10 * cold_bonus)

def detect_pattern(h, length=3):
    if len(h) < length * 2 + 1:
        return None
    recent = tuple(h[:length])
    for i in range(length, len(h) - length):
        if tuple(h[i:i + length]) == recent:
            return h[i - 1] if i > 0 else None
    return None

def get_micro_sfasamento(h, window=15):
    result = {}
    recent = h[:window] if len(h) >= window else h
    for seg in SEGMENTS:
        zona = [seg] + NEIGHBORS.get(seg, [])
        gaps = [i for i, v in enumerate(recent) if v in zona]
        result[seg] = gaps[0] if gaps else window
    return result

# INTERFACCIA
st.title("CT Oracle Pro v2 - Markov + Settore + Pattern + Chi2")

# TOP BAR
t1, t2, t3, t4, t5 = st.columns(5)
current_rtp = t1.number_input("RTP Live (%)", min_value=0.0, value=96.0, step=0.1)
t2.metric("Giri Totali", st.session_state.total_spins)
t3.metric("Giri Dealer", st.session_state.dealer_spins)
sfas_gen = get_sfasamento(st.session_state.history) if st.session_state.history else 0
t4.metric("Sfas. Bonus", sfas_gen)

chi2 = get_chi_square(st.session_state.history) if len(st.session_state.history) >= 15 else None
if chi2 is not None:
    label = "BIAS!" if chi2 > 14.07 else "Random"
    t5.metric("Chi2 Bias Detector", f"{chi2:.1f}", delta=label,
              delta_color="normal" if chi2 < 14.07 else "off")

st.markdown("---")

# TASTIERA INPUT
st.write("### Inserimento Rapido")
cols_btn = st.columns(8)
for idx, seg in enumerate(SEGMENTS):
    if cols_btn[idx].button(seg, use_container_width=True, key=f"btn_{seg}"):
        st.session_state.history.insert(0, seg)
        st.session_state.dealer_history.insert(0, seg)
        st.session_state.total_spins += 1
        st.session_state.dealer_spins += 1
        st.rerun()

# NASTRO STORICO COLORATO
if st.session_state.history:
    st.write("**Ultimi 20 giri** (da sinistra = più recente):")
    recent20 = st.session_state.history[:20]
    hist_cols = st.columns(len(recent20))
    for idx, (col, val) in enumerate(zip(hist_cols, recent20)):
        if is_bonus(val):
            col.markdown(
                f"<div style='background:#c0392b;border-radius:6px;text-align:center;padding:4px 2px;font-size:10px;color:white;font-weight:bold'>{val[:4]}</div>",
                unsafe_allow_html=True)
        else:
            col.markdown(
                f"<div style='background:#2c3e50;border-radius:6px;text-align:center;padding:4px 2px;font-size:10px;color:#ecf0f1'>{val}</div>",
                unsafe_allow_html=True)

st.markdown("---")

# MOTORE PRINCIPALE
if len(st.session_state.history) > 5:
    h = st.session_state.history
    markov, ent_total, ent_recent = get_analysis_weighted(h)
    last = h[0]
    hot, cold = get_hot_cold(h)
    micro_sfas = get_micro_sfasamento(h)

    col1, col2, col3 = st.columns([1, 1, 1.5])

    # COL 1: STATO MOTORE
    with col1:
        st.subheader("Stato Motore")
        st.metric("Ultimo", last)
        st.metric("Entropia Recente (15 giri)", f"{ent_recent:.2f}")

        if ent_recent < 1.85:
            st.success("PUNTUALE - Motore predicibile")
        elif ent_recent < 2.2:
            st.warning("INTERMEDIO - Analisi con cautela")
        else:
            st.error("CAOTICO - Rumore bianco, salta")

        if chi2 and chi2 > 18.48:
            st.error(f"BIAS FORTE (chi2={chi2:.1f}) - La ruota ha pattern!")
        elif chi2 and chi2 > 14.07:
            st.warning(f"Possibile Bias (chi2={chi2:.1f})")

        if hot:
            st.write("HOT:", ", ".join(hot.keys()))
        if cold:
            st.write("COLD (dovuti):", ", ".join(cold.keys()))

    # COL 2: MARKOV + SCORE COMPOSITO
    with col2:
        st.subheader("Markov Pesato + Score")
        preds = markov.loc[last].sort_values(ascending=False).head(4)
        markov_fav = preds.index[0] if not preds.empty and preds.iloc[0] > 0 else None

        for val, prob in preds.items():
            if prob <= 0:
                continue
            score = get_composite_score(h, val, prob)
            trend = get_trend(h, val)
            t_arrow = "SU" if trend > 0.2 else ("GIU" if trend < -0.2 else "STABILE")
            dot = "[FORTE]" if score > 0.55 else ("[MED]" if score > 0.35 else "[DEBOLE]")
            msfas = micro_sfas.get(val, 0)

            st.write(f"{dot} **{val}** ({t_arrow})")
            st.caption(
                f"Markov: {prob:.1%} | Score: {score:.2f} | "
                f"Zona gap: {msfas} | Vicini: {', '.join(NEIGHBORS.get(val,[])[:2])}"
            )

    # COL 3: RADAR BONUS
    with col3:
        st.subheader("Radar Bonus - Urgenza")

        bonus_data = []
        for bonus in BONUS_LIST:
            sfas = get_sfasamento(h, bonus)
            exp_gap = 1 / EXPECTED_FREQ[bonus]
            urgency = sfas / exp_gap
            mk_prob = markov.loc[last].get(bonus, 0)
            score_b = get_composite_score(h, bonus, mk_prob)
            bonus_data.append((bonus, sfas, urgency, score_b))

        bonus_data.sort(key=lambda x: x[2], reverse=True)

        for bonus, sfas, urgency, score_b in bonus_data:
            exp_gap_val = round(1 / EXPECTED_FREQ[bonus])
            if urgency > 1.8:
                st.error(f"ATTACCO: **{bonus}** | Gap: {sfas}/{exp_gap_val} | Urgenza: {urgency:.1f}x | Score: {score_b:.2f}")
            elif urgency > 1.0:
                st.warning(f"MONITOR: **{bonus}** | Gap: {sfas}/{exp_gap_val} | Urgenza: {urgency:.1f}x")
            else:
                st.info(f"ATTESA: {bonus} | Gap: {sfas}/{exp_gap_val}")

        if markov_fav and markov_fav in CORRELATION_MAP:
            st.write(f"**Bonus correlati a {markov_fav}:**")
            for tb in CORRELATION_MAP[markov_fav]:
                sfas_tb = get_sfasamento(h, tb)
                exp_tb = round(1 / EXPECTED_FREQ[tb])
                if sfas_tb > exp_tb * 1.2:
                    st.error(f"ATTACCO: **{tb}** (Gap: {sfas_tb})")
                else:
                    st.info(f"Monitor: {tb} (Gap: {sfas_tb})")

    st.markdown("---")

    # PATTERN DETECTOR
    pattern_pred = detect_pattern(h, length=3)
    if pattern_pred:
        st.info(f"PATTERN DETECTOR: Sequenza recente già apparsa. Successivo previsto: **{pattern_pred}**")

    # FREQUENZE vs ATTESO
    with st.expander("Frequenze Osservate vs Attese (click per aprire)"):
        freq_rows = []
        counts_all = Counter(h)
        n_all = len(h)
        for seg in SEGMENTS:
            obs_n = counts_all.get(seg, 0)
            obs_pct = obs_n / n_all
            exp_pct = EXPECTED_FREQ[seg]
            dev = (obs_pct - exp_pct) / exp_pct * 100
            sfas_s = get_sfasamento(h, seg)
            exp_gap_s = round(1 / exp_pct)
            freq_rows.append({
                'Segmento': seg,
                'Obs #': obs_n,
                'Obs %': f"{obs_pct:.1%}",
                'Atteso %': f"{exp_pct:.1%}",
                'Deviazione': f"{dev:+.0f}%",
                'Gap attuale': sfas_s,
                'Gap atteso': f"~{exp_gap_s}",
                'Urgenza': f"{sfas_s/exp_gap_s:.1f}x",
            })
        st.dataframe(pd.DataFrame(freq_rows), use_container_width=True, hide_index=True)

    # TATTICA AUTOMATICA
    st.subheader("Manuale di Giocata - Tattica Automatica")
    top_bonus, top_sfas, top_urgency, top_score = bonus_data[0]

    if current_rtp < 89 and ent_recent < 1.9 and top_urgency > 1.2:
        st.success(f"ATTACCO AL SETTORE | Markov: **{markov_fav}** | Bonus urgente: **{top_bonus}** (Gap {top_sfas}, urgenza {top_urgency:.1f}x) | Copri il numero + bonus correlati.")
    elif current_rtp > 115:
        st.error("RECUPERO BANCO | RTP critico. Banca in vantaggio: gioca solo 1-2 per stabilizzare.")
    elif top_urgency > 2.0:
        st.warning(f"BONUS IN PRESSIONE | **{top_bonus}** a {top_sfas} giri dal previsto {round(1/EXPECTED_FREQ[top_bonus])}. Considera copertura selettiva.")
    elif ent_recent > 2.5:
        st.error("MOTORE CAOTICO | Non entrare. Attendi entropia < 2.0.")
    else:
        st.info(f"ATTESA STATISTICA | Sfasamento generale: {sfas_gen}. Entra quando sfasamento > 10 e urgenza bonus > 1.2.")

    # PROFILO DEALER
    if len(st.session_state.dealer_history) >= 10:
        dh = st.session_state.dealer_history
        _, _, ent_dealer = get_analysis_weighted(dh)
        with st.expander("Profilo Dealer Corrente"):
            st.write(f"Giri dealer: **{st.session_state.dealer_spins}**")
            st.write(f"Entropia dealer: **{ent_dealer:.2f}**")
            dc = Counter(dh)
            dealer_df = pd.DataFrame([
                {'Segmento': s, 'Uscite dealer': dc.get(s, 0), 'Freq %': f"{dc.get(s, 0)/len(dh):.1%}"}
                for s in SEGMENTS
            ])
            st.dataframe(dealer_df, use_container_width=True, hide_index=True)

# SIDEBAR
st.sidebar.header("Controlli")

if st.sidebar.button("Cancella Ultimo"):
    if st.session_state.history:
        st.session_state.history.pop(0)
        st.session_state.total_spins = max(0, st.session_state.total_spins - 1)
    if st.session_state.dealer_history:
        st.session_state.dealer_history.pop(0)
        st.session_state.dealer_spins = max(0, st.session_state.dealer_spins - 1)
    st.rerun()

if st.sidebar.button("Cambio Dealer"):
    st.session_state.dealer_spins = 0
    st.session_state.dealer_history = []
    st.rerun()

if st.sidebar.button("Reset Totale"):
    st.session_state.history.clear()
    st.session_state.dealer_history.clear()
    st.session_state.total_spins = 0
    st.session_state.dealer_spins = 0
    st.rerun()

if st.session_state.history:
    st.sidebar.markdown("---")
    st.sidebar.write("**Gap Bonus:**")
    for bonus in BONUS_LIST:
        sfas_b = get_sfasamento(st.session_state.history, bonus)
        exp_b = round(1 / EXPECTED_FREQ[bonus])
        urg = sfas_b / exp_b
        icon = "ATTACCO" if urg > 1.8 else ("MONITOR" if urg > 1.0 else "ATTESA")
        st.sidebar.write(f"{icon} | {bonus}: {sfas_b}/{exp_b} ({urg:.1f}x)")

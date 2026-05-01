import streamlit as st
import numpy as np
import pandas as pd
from collections import Counter, deque
from scipy import stats
import math

# --- CONFIGURAZIONE UI APPLE DARK PRO ---
st.set_page_config(page_title='Roulette Analytics Pro V8.0', layout='wide', initial_sidebar_state='expanded')

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #F5F5F7; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .glass-box { background: rgba(28, 28, 30, 0.8); backdrop-filter: blur(20px); border-radius: 16px; padding: 22px; border: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 16px; }
    .stat-card { background: linear-gradient(135deg, #161618 0%, #222224 100%); border-radius: 16px; padding: 20px; border: 1px solid #333; margin-bottom: 12px; }
    .stat-card-alert { background: linear-gradient(135deg, #4A0A0A 0%, #221100 100%); border-radius: 16px; padding: 20px; border: 1px solid #FF3B30; box-shadow: 0 8px 30px rgba(255,59,48,0.15); }
    .stat-card-success { background: linear-gradient(135deg, #0A4A2A 0%, #002211 100%); border-radius: 16px; padding: 20px; border: 1px solid #32D74B; box-shadow: 0 8px 30px rgba(50,215,75,0.15); }
    .stat-card-warning { background: linear-gradient(135deg, #4A2A0A 0%, #221100 100%); border-radius: 16px; padding: 20px; border: 1px solid #FF9F0A; box-shadow: 0 8px 30px rgba(255,159,10,0.15); }
    .numpad-btn>button { border-radius: 8px; background-color: #1A1A1C; color: white; border: 1px solid #2C2C2E; height: 55px; font-weight: 700; font-size: 20px; transition: all 0.1s; }
    .numpad-btn>button:active { transform: scale(0.95); }
    .btn-red>button { border-bottom: 4px solid #FF3B30; }
    .btn-black>button { border-bottom: 4px solid #636366; }
    .btn-zero>button { border-bottom: 4px solid #32D74B; background-color: rgba(50, 215, 75, 0.05); }
    .num-badge { display: inline-block; width: 42px; height: 42px; line-height: 42px; text-align: center; border-radius: 50%; font-weight: bold; font-size: 16px; margin: 3px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
    .badge-red { background: #FF3B30; color: white; border: 2px solid #FF453A; }
    .badge-black { background: #1C1C1E; color: white; border: 2px solid #3A3A3C; }
    .badge-zero { background: #32D74B; color: black; border: 2px solid #28CD41; }
    .badge-hot { box-shadow: 0 0 15px rgba(255,149,0,0.8); border: 2px solid #FF9F0A; }
    .badge-cold { opacity: 0.5; border: 2px solid #636366; }
    .row-badge { display: inline-block; padding: 8px 16px; border-radius: 8px; font-weight: bold; font-size: 14px; margin: 3px; }
    .row-1 { background: linear-gradient(135deg, #FF3B30 0%, #FF453A 100%); color: white; }
    .row-2 { background: linear-gradient(135deg, #1C1C1E 0%, #3A3A3C 100%); color: white; }
    .row-3 { background: linear-gradient(135deg, #0A84FF 0%, #5E5CE6 100%); color: white; }
    .row-0 { background: linear-gradient(135deg, #32D74B 0%, #28CD41 100%); color: black; }
    .metric-label { font-size: 12px; color: #8E8E93; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-value { font-size: 28px; font-weight: 700; color: #F5F5F7; }
    .metric-delta { font-size: 14px; color: #8E8E93; }
    .prediction-box { background: linear-gradient(135deg, #0A2A4A 0%, #001122 100%); border-radius: 20px; padding: 25px; border: 2px solid #0A84FF; box-shadow: 0 10px 40px rgba(10,132,255,0.3); margin: 20px 0; }
    </style>
""", unsafe_allow_html=True)

# --- COSTANTI ---
WHEEL = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]
RED_NUMS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

# ROWS (righe del tavolo)
ROW_1 = {1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34}
ROW_2 = {2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35}
ROW_3 = {3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36}

SECTORS = {
    'Voisins': [22, 18, 29, 7, 28, 12, 35, 3, 26, 0, 32, 15, 19, 4, 21, 2, 25],
    'Tiers': [27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33],
    'Orphelins': [1, 20, 14, 31, 9, 17, 34, 6],
    'Zero': [12, 35, 3, 26, 0, 32, 15]
}

# --- SESSION STATE ---
if 'history' not in st.session_state:
    st.session_state.update({
        'history': [],
        'bankroll': 1000.0,
        'initial_bankroll': 1000.0,
        'bet_history': [],
        'last_bet': None,
        'row_sequence': [],
        'transition_matrix': {}
    })

# --- FUNZIONI CORE ---
def get_row(n):
    """Ritorna la riga del numero (1, 2, 3, 0 per zero)"""
    if n == 0:
        return 0
    elif n in ROW_1:
        return 1
    elif n in ROW_2:
        return 2
    elif n in ROW_3:
        return 3
    return 0

def get_row_numbers(row):
    """Ritorna i numeri di una riga"""
    if row == 1:
        return sorted(list(ROW_1))
    elif row == 2:
        return sorted(list(ROW_2))
    elif row == 3:
        return sorted(list(ROW_3))
    return [0]

def get_color_class(n, hot_nums=None, cold_nums=None):
    base = "badge-zero" if n == 0 else ("badge-red" if n in RED_NUMS else "badge-black")
    if hot_nums and n in hot_nums:
        base += " badge-hot"
    elif cold_nums and n in cold_nums:
        base += " badge-cold"
    return base

def get_row_class(row):
    return f"row-{row}"

# --- ANALISI RIGHE ---
def analyze_row_sequences(history):
    """Analizza sequenze consecutive di righe"""
    if len(history) < 5:
        return {}
    
    row_seq = [get_row(n) for n in history]
    
    # Trova streak corrente
    current_streak = 1
    current_row = row_seq[0]
    for r in row_seq[1:]:
        if r == current_row and r != 0:  # Non contare zero
            current_streak += 1
        else:
            break
    
    # Trova max streak per ogni riga
    max_streaks = {1: 0, 2: 0, 3: 0}
    streak = 1
    prev_row = row_seq[0]
    
    for r in row_seq[1:]:
        if r == prev_row and r != 0:
            streak += 1
        else:
            if prev_row != 0:
                max_streaks[prev_row] = max(max_streaks[prev_row], streak)
            streak = 1
            prev_row = r
    
    if prev_row != 0:
        max_streaks[prev_row] = max(max_streaks[prev_row], streak)
    
    # Calcola statistiche
    row_counts = Counter([r for r in row_seq if r != 0])
    total_non_zero = sum(row_counts.values())
    
    stats = {
        'current_row': current_row,
        'current_streak': current_streak,
        'max_streaks': max_streaks,
        'row_counts': row_counts,
        'row_percentages': {r: (count / total_non_zero * 100) if total_non_zero > 0 else 0 
                           for r, count in row_counts.items()},
        'total_spins': len(row_seq),
        'zero_count': row_seq.count(0)
    }
    
    return stats

def build_transition_matrix(history):
    """Costruisce matrice di transizione tra righe"""
    if len(history) < 10:
        return {}
    
    row_seq = [get_row(n) for n in history if get_row(n) != 0]  # Escludi zero
    
    transitions = {}
    for i in range(len(row_seq) - 1):
        from_row = row_seq[i]
        to_row = row_seq[i + 1]
        
        key = f"{from_row}->{to_row}"
        transitions[key] = transitions.get(key, 0) + 1
    
    # Normalizza per probabilità
    transition_probs = {}
    for from_row in [1, 2, 3]:
        total = sum(transitions.get(f"{from_row}->{to}", 0) for to in [1, 2, 3])
        if total > 0:
            for to_row in [1, 2, 3]:
                key = f"{from_row}->{to_row}"
                count = transitions.get(key, 0)
                transition_probs[key] = {
                    'count': count,
                    'probability': count / total,
                    'percentage': (count / total * 100)
                }
    
    return transition_probs

def predict_next_rows(history, streak_threshold=3):
    """Sistema predittivo anti-streak: suggerisce righe dopo streak"""
    if len(history) < 5:
        return None
    
    row_stats = analyze_row_sequences(history)
    
    # Se la riga corrente ha uno streak >= threshold, suggerisci le altre 2
    if row_stats['current_streak'] >= streak_threshold and row_stats['current_row'] != 0:
        current = row_stats['current_row']
        suggested_rows = [r for r in [1, 2, 3] if r != current]
        
        # Calcola probabilità empirica basata su transition matrix
        trans_matrix = build_transition_matrix(history)
        
        # Ordina le righe suggerite per probabilità di transizione
        row_probs = {}
        for row in suggested_rows:
            key = f"{current}->{row}"
            prob_data = trans_matrix.get(key, {'probability': 1/3, 'count': 0})
            row_probs[row] = prob_data['probability']
        
        # Ordina per probabilità decrescente
        sorted_rows = sorted(suggested_rows, key=lambda r: row_probs[r], reverse=True)
        
        return {
            'type': 'anti_streak',
            'reason': f'Riga {current} uscita {row_stats["current_streak"]} volte consecutive',
            'suggested_rows': sorted_rows,
            'probabilities': row_probs,
            'confidence': min(row_stats['current_streak'] / 5 * 100, 85)  # Max 85% confidence
        }
    
    # Altrimenti analizza distribuzione
    total_non_zero = sum(row_stats['row_counts'].values())
    if total_non_zero >= 20:
        # Trova riga più "fredda" (meno uscita)
        expected = total_non_zero / 3
        deviations = {}
        for row in [1, 2, 3]:
            count = row_stats['row_counts'].get(row, 0)
            deviation = count - expected
            deviations[row] = deviation
        
        # Suggerisci le 2 righe più fredde
        sorted_by_cold = sorted([1, 2, 3], key=lambda r: deviations[r])
        
        if deviations[sorted_by_cold[0]] < -expected * 0.15:  # Almeno 15% sotto media
            return {
                'type': 'cold_bias',
                'reason': f'Riga {sorted_by_cold[0]} uscita solo {row_stats["row_counts"].get(sorted_by_cold[0], 0)} volte (exp: {expected:.1f})',
                'suggested_rows': sorted_by_cold[:2],
                'probabilities': {r: (1 - deviations[r] / expected) / 2 for r in sorted_by_cold[:2]},
                'confidence': min(abs(deviations[sorted_by_cold[0]]) / expected * 100, 70)
            }
    
    return None

# --- STATISTICA CLASSICA ---
def chi_square_test(history):
    if len(history) < 37:
        return None, None
    observed = Counter(history)
    expected = len(history) / 37
    chi_sq = sum((observed.get(i, 0) - expected)**2 / expected for i in range(37))
    p_value = 1 - stats.chi2.cdf(chi_sq, df=36)
    return chi_sq, p_value

def calculate_z_scores(history):
    if len(history) < 50:
        return {}
    n_spins = len(history)
    expected_freq = n_spins / 37
    expected_std = math.sqrt(n_spins * (1/37) * (36/37))
    observed = Counter(history)
    z_scores = {}
    for num in range(37):
        obs_freq = observed.get(num, 0)
        z = (obs_freq - expected_freq) / expected_std if expected_std > 0 else 0
        z_scores[num] = z
    return z_scores

def identify_hot_cold(z_scores, threshold=1.96):
    hot = [n for n, z in z_scores.items() if z > threshold]
    cold = [n for n, z in z_scores.items() if z < -threshold]
    return hot, cold

def runs_test(history):
    if len(history) < 20:
        return None, None
    sequence = [1 if n in RED_NUMS else 0 for n in history]
    n1 = sum(sequence)
    n2 = len(sequence) - n1
    if n1 == 0 or n2 == 0:
        return None, None
    runs = 1
    for i in range(1, len(sequence)):
        if sequence[i] != sequence[i-1]:
            runs += 1
    expected_runs = (2 * n1 * n2) / (n1 + n2) + 1
    std_runs = math.sqrt((2 * n1 * n2 * (2 * n1 * n2 - n1 - n2)) / 
                         ((n1 + n2)**2 * (n1 + n2 - 1)))
    if std_runs == 0:
        return None, None
    z_stat = (runs - expected_runs) / std_runs
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    return z_stat, p_value

def calculate_kelly_fraction(win_prob, odds, max_fraction=0.05):
    if win_prob <= 0 or win_prob >= 1:
        return 0.0
    kelly = ((odds * win_prob) - (1 - win_prob)) / odds
    return max(0, min(kelly * 0.25, max_fraction))

def get_sector(n):
    for sec, nums in SECTORS.items():
        if n in nums:
            return sec
    return 'Voisins'

def sector_analysis(history):
    if len(history) < 30:
        return {}
    sector_counts = Counter(get_sector(n) for n in history)
    total = len(history)
    analysis = {}
    for sector, nums in SECTORS.items():
        observed = sector_counts.get(sector, 0)
        expected = total * (len(nums) / 37)
        deviation = ((observed - expected) / expected * 100) if expected > 0 else 0
        analysis[sector] = {
            'count': observed,
            'expected': expected,
            'deviation': deviation,
            'percentage': (observed / total * 100) if total > 0 else 0
        }
    return analysis

# --- PROCESS INPUT ---
def process_input(val):
    st.session_state.history.insert(0, val)
    st.session_state.row_sequence.insert(0, get_row(val))
    
    # Process bet
    if st.session_state.last_bet:
        bet_type, bet_target, bet_amount = st.session_state.last_bet
        
        if bet_type == 'rows':
            # Bet su righe: payout 2:1
            if get_row(val) in bet_target:
                payout = bet_amount * 3  # Stake + 2x profit
                profit = payout - bet_amount
                result = 'WIN'
            else:
                profit = -bet_amount
                result = 'LOSS'
        else:
            # Bet su numeri: payout 35:1
            if val in bet_target:
                payout = bet_amount * 36
                profit = payout - bet_amount
                result = 'WIN'
            else:
                profit = -bet_amount
                result = 'LOSS'
        
        st.session_state.bankroll += profit
        
        st.session_state.bet_history.insert(0, {
            'spin': val,
            'bet_type': bet_type,
            'bet_target': bet_target,
            'bet_amount': bet_amount,
            'profit': profit,
            'result': result,
            'bankroll': st.session_state.bankroll
        })
        
        st.session_state.last_bet = None
    
    st.rerun()

# --- SIDEBAR ---
st.sidebar.title("🛠️ Pannello Controllo")

st.sidebar.markdown("### 💰 Bankroll Management")
current_br = st.session_state.bankroll
initial_br = st.session_state.initial_bankroll
br_change = ((current_br - initial_br) / initial_br * 100) if initial_br > 0 else 0
br_color = "#32D74B" if br_change >= 0 else "#FF3B30"

st.sidebar.markdown(f"""
<div class="stat-card">
    <div class="metric-label">Bankroll Attuale</div>
    <div class="metric-value">{current_br:.2f}€</div>
    <div class="metric-delta" style="color:{br_color};">{br_change:+.1f}% ({current_br - initial_br:+.2f}€)</div>
</div>
""", unsafe_allow_html=True)

new_bankroll = st.sidebar.number_input("Reset Bankroll", min_value=100.0, value=1000.0, step=100.0)
if st.sidebar.button("💵 Aggiorna Bankroll", use_container_width=True):
    st.session_state.bankroll = new_bankroll
    st.session_state.initial_bankroll = new_bankroll
    st.rerun()

st.sidebar.markdown("---")

# Threshold per anti-streak
streak_threshold = st.sidebar.slider("🎯 Soglia Anti-Streak", min_value=2, max_value=5, value=3, 
                                     help="Dopo quanti spin consecutivi della stessa riga attivare predizione")

if st.sidebar.button("⏪ Annulla Ultimo Spin", use_container_width=True):
    if st.session_state.history:
        st.session_state.history.pop(0)
        if st.session_state.row_sequence:
            st.session_state.row_sequence.pop(0)
        if st.session_state.bet_history:
            last_bet_result = st.session_state.bet_history.pop(0)
            st.session_state.bankroll -= last_bet_result['profit']
        st.rerun()

if st.sidebar.button("🗑️ Reset Sessione", use_container_width=True):
    st.session_state.history = []
    st.session_state.row_sequence = []
    st.session_state.bet_history = []
    st.session_state.last_bet = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ Analytics Pro V8.0")
st.sidebar.caption("Sistema predittivo anti-streak per righe + analisi statistica completa.")

# --- MAIN UI ---
st.title("📊 Roulette Analytics Pro V8.0")

# METRICHE
m1, m2, m3, m4 = st.columns(4)
total_spins = len(st.session_state.history)
total_bets = len(st.session_state.bet_history)
wins = sum(1 for b in st.session_state.bet_history if b['result'] == 'WIN')
win_rate = (wins / total_bets * 100) if total_bets > 0 else 0.0

m1.metric("Spins Totali", total_spins)
m2.metric("Bets Placed", total_bets)
m3.metric("Win Rate", f"{win_rate:.1f}%")
m4.metric("ROI", f"{br_change:.1f}%")

st.markdown("---")

# LAYOUT
col_input, col_analysis = st.columns([1, 2.5])

# --- INPUT ---
with col_input:
    st.markdown("### 🎛️ Input Numero")
    
    st.markdown('<div class="btn-zero numpad-btn">', unsafe_allow_html=True)
    if st.button("0", use_container_width=True):
        process_input(0)
    st.markdown('</div>', unsafe_allow_html=True)
    
    for r in range(12):
        cols = st.columns(3)
        for i, col in enumerate(cols):
            val = r * 3 + i + 1
            btn_class = "btn-red" if val in RED_NUMS else "btn-black"
            with col:
                st.markdown(f'<div class="{btn_class} numpad-btn">', unsafe_allow_html=True)
                if st.button(str(val), key=f'b_{val}', use_container_width=True):
                    process_input(val)
                st.markdown('</div>', unsafe_allow_html=True)

# --- ANALYSIS ---
with col_analysis:
    if st.session_state.history:
        st.markdown("**📜 Cronologia (Ultimi 20 Spins):**")
        
        z_scores = calculate_z_scores(st.session_state.history)
        hot_nums, cold_nums = identify_hot_cold(z_scores, threshold=1.96)
        
        html_h = '<div style="display:flex; flex-wrap:wrap; margin-bottom:20px;">'
        for v in st.session_state.history[:20]:
            html_h += f'<div class="num-badge {get_color_class(v, hot_nums, cold_nums)}">{v}</div>'
        html_h += '</div>'
        st.markdown(html_h, unsafe_allow_html=True)
        
        # --- ROW SEQUENCE ---
        st.markdown("**🎯 Sequenza Righe (Ultimi 15):**")
        html_r = '<div style="display:flex; flex-wrap:wrap; margin-bottom:20px;">'
        for row in st.session_state.row_sequence[:15]:
            row_label = f"R{row}" if row != 0 else "0"
            html_r += f'<div class="row-badge {get_row_class(row)}">{row_label}</div>'
        html_r += '</div>'
        st.markdown(html_r, unsafe_allow_html=True)
        
        # --- ANALISI RIGHE ---
        if total_spins >= 10:
            row_stats = analyze_row_sequences(st.session_state.history)
            trans_matrix = build_transition_matrix(st.session_state.history)
            
            st.markdown("### 📊 Analisi Righe")
            
            r1, r2, r3 = st.columns(3)
            
            for idx, row_num in enumerate([1, 2, 3]):
                with [r1, r2, r3][idx]:
                    count = row_stats['row_counts'].get(row_num, 0)
                    pct = row_stats['row_percentages'].get(row_num, 0)
                    max_streak = row_stats['max_streaks'].get(row_num, 0)
                    
                    is_current = (row_stats['current_row'] == row_num)
                    border_color = "#0A84FF" if is_current else "#333"
                    
                    st.markdown(f"""
                    <div class="stat-card" style="border: 2px solid {border_color};">
                        <div style="font-weight:700; font-size:16px; margin-bottom:8px;">
                            Riga {row_num} {' 🔥 STREAK' if is_current and row_stats['current_streak'] >= streak_threshold else ''}
                        </div>
                        <div style="font-size:32px; font-weight:700; color:#F5F5F7;">{count}</div>
                        <div style="font-size:14px; color:#8E8E93;">
                            {pct:.1f}% (exp: 33.3%)<br>
                            Max Streak: {max_streak}
                        </div>
                        {f'<div style="margin-top:8px; color:#FF9F0A; font-weight:600;">ATTUALE: {row_stats["current_streak"]} consecutivi</div>' if is_current else ''}
                    </div>
                    """, unsafe_allow_html=True)
            
            # --- SISTEMA PREDITTIVO ---
            prediction = predict_next_rows(st.session_state.history, streak_threshold=streak_threshold)
            
            if prediction:
                st.markdown('<div class="prediction-box">', unsafe_allow_html=True)
                st.markdown(f"""
                    <div style="font-size:20px; font-weight:700; color:#0A84FF; margin-bottom:12px;">
                        🎯 PREDIZIONE ATTIVA
                    </div>
                    <div style="font-size:15px; color:#A1A1A6; margin-bottom:15px;">
                        <b>Tipo:</b> {prediction['type'].upper()}<br>
                        <b>Motivo:</b> {prediction['reason']}<br>
                        <b>Confidence:</b> {prediction['confidence']:.0f}%
                    </div>
                    <div style="font-size:16px; font-weight:600; margin-bottom:10px; color:white;">
                        PUNTA SULLE RIGHE:
                    </div>
                """, unsafe_allow_html=True)
                
                html_pred = '<div style="display:flex; gap:12px; margin-bottom:15px;">'
                for row in prediction['suggested_rows']:
                    prob = prediction['probabilities'].get(row, 0) * 100
                    html_pred += f'<div class="row-badge {get_row_class(row)}" style="padding:12px 24px; font-size:18px;">Riga {row}<br><span style="font-size:12px;">p={prob:.0f}%</span></div>'
                html_pred += '</div>'
                st.markdown(html_pred, unsafe_allow_html=True)
                
                # Kelly sizing per righe (payout 2:1)
                avg_prob = sum(prediction['probabilities'].values()) / len(prediction['probabilities']) if prediction['probabilities'] else 0.33
                kelly_fraction = calculate_kelly_fraction(avg_prob, 2, max_fraction=0.10)  # Max 10% per righe
                suggested_bet_per_row = (current_br * kelly_fraction) / len(prediction['suggested_rows'])
                total_bet = suggested_bet_per_row * len(prediction['suggested_rows'])
                
                st.markdown(f"""
                    <div style="font-size:14px; color:#A1A1A6; margin-top:10px;">
                        <b>Kelly Sizing:</b> {suggested_bet_per_row:.2f}€ per riga ({total_bet:.2f}€ totali)<br>
                        <b>Payout:</b> 2:1 (ritorno 3x su singola riga vincente)<br>
                        <b>Note:</b> Fractional Kelly (1/4) per risk management
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Button per piazzare bet
                if st.button(f"🎰 Piazza Bet ({total_bet:.2f}€ totali)", use_container_width=True, key='bet_pred'):
                    st.session_state.last_bet = ('rows', prediction['suggested_rows'], total_bet)
                    st.success(f"✅ Bet piazzato: {total_bet:.2f}€ su Righe {prediction['suggested_rows']}")
            
            # --- TRANSITION MATRIX ---
            if trans_matrix and total_spins >= 20:
                st.markdown("### 🔄 Matrice di Transizione Righe")
                st.caption("Probabilità empiriche di cambio riga")
                
                trans_df_data = []
                for from_row in [1, 2, 3]:
                    row_data = {'Da Riga': f'Riga {from_row}'}
                    for to_row in [1, 2, 3]:
                        key = f"{from_row}->{to_row}"
                        data = trans_matrix.get(key, {'count': 0, 'percentage': 0})
                        row_data[f'→ R{to_row}'] = f"{data['percentage']:.1f}% ({data['count']})"
                    trans_df_data.append(row_data)
                
                trans_df = pd.DataFrame(trans_df_data)
                st.dataframe(trans_df, use_container_width=True, hide_index=True)
        
        # --- ANALISI STATISTICA CLASSICA ---
        if total_spins >= 37:
            st.markdown("---")
            st.markdown("### 📈 Test Statistici Fairness")
            
            chi_sq, p_value = chi_square_test(st.session_state.history)
            runs_z, runs_p = runs_test(st.session_state.history)
            
            col_chi, col_runs = st.columns(2)
            
            with col_chi:
                if p_value is not None:
                    is_fair = p_value > 0.05
                    card_class = "stat-card-success" if is_fair else "stat-card-alert"
                    status_text = "✅ FAIR" if is_fair else "⚠️ BIASED"
                    status_color = "#32D74B" if is_fair else "#FF3B30"
                    
                    st.markdown(f"""
                    <div class="{card_class}">
                        <div class="metric-label">Chi-Square Test</div>
                        <div class="metric-value" style="color:{status_color};">{status_text}</div>
                        <div class="metric-delta">χ² = {chi_sq:.2f}, p = {p_value:.4f}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            with col_runs:
                if runs_p is not None:
                    is_random = runs_p > 0.05
                    card_class = "stat-card-success" if is_random else "stat-card-alert"
                    status_text = "✅ RANDOM" if is_random else "⚠️ PATTERN"
                    status_color = "#32D74B" if is_random else "#FF3B30"
                    
                    st.markdown(f"""
                    <div class="{card_class}">
                        <div class="metric-label">Runs Test</div>
                        <div class="metric-value" style="color:{status_color};">{status_text}</div>
                        <div class="metric-delta">Z = {runs_z:.2f}, p = {runs_p:.4f}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Hot/Cold
            if len(z_scores) > 0:
                st.markdown("### 🔥 Hot/Cold Numbers")
                col_hot, col_cold = st.columns(2)
                
                with col_hot:
                    st.markdown('<div class="glass-box">', unsafe_allow_html=True)
                    st.markdown("**🔥 HOT (z > +1.96)**")
                    if hot_nums:
                        hot_sorted = sorted(hot_nums, key=lambda n: z_scores[n], reverse=True)[:8]
                        for num in hot_sorted:
                            freq = Counter(st.session_state.history)[num]
                            st.markdown(f"**{num}**: {freq} (z={z_scores[num]:.2f})")
                    else:
                        st.caption("Nessun numero hot")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col_cold:
                    st.markdown('<div class="glass-box">', unsafe_allow_html=True)
                    st.markdown("**❄️ COLD (z < -1.96)**")
                    if cold_nums:
                        cold_sorted = sorted(cold_nums, key=lambda n: z_scores[n])[:8]
                        for num in cold_sorted:
                            freq = Counter(st.session_state.history)[num]
                            st.markdown(f"**{num}**: {freq} (z={z_scores[num]:.2f})")
                    else:
                        st.caption("Nessun numero cold")
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # Sector analysis
            sector_stats = sector_analysis(st.session_state.history)
            if sector_stats:
                st.markdown("### 🎯 Analisi Settori")
                sector_cols = st.columns(len(SECTORS))
                for idx, (sector, data) in enumerate(sector_stats.items()):
                    with sector_cols[idx]:
                        deviation_color = "#32D74B" if abs(data['deviation']) < 10 else ("#FF9F0A" if abs(data['deviation']) < 20 else "#FF3B30")
                        st.markdown(f"""
                        <div class="glass-box">
                            <div style="font-weight:700; font-size:14px;">{sector}</div>
                            <div style="font-size:24px; font-weight:700;">{data['count']}</div>
                            <div style="font-size:12px; color:#8E8E93;">exp: {data['expected']:.1f}</div>
                            <div style="font-size:14px; color:{deviation_color};">{data['deviation']:+.1f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
        
        elif total_spins >= 10:
            st.info("🟡 Inserisci almeno 37 spins per test statistici completi.")
        else:
            st.info("🟡 Inserisci almeno 10 spins per iniziare l'analisi.")
    
    else:
        st.info("🎲 Inserisci i numeri per iniziare l'analisi.")

# --- BET HISTORY ---
if st.session_state.bet_history:
    st.markdown("---")
    st.markdown("### 📊 Storico Bets (Ultimi 10)")
    
    bet_df = pd.DataFrame(st.session_state.bet_history[:10])
    bet_df_display = bet_df[['spin', 'bet_type', 'result', 'bet_amount', 'profit', 'bankroll']].copy()
    bet_df_display.columns = ['Spin', 'Tipo', 'Result', 'Bet (€)', 'Profit (€)', 'Bankroll (€)']
    
    st.dataframe(bet_df_display, use_container_width=True, hide_index=True)

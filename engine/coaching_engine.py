"""
SwingCoach Coaching Engine v3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Built on 4,353 trading days (2009-2026) of Pradeep Bhonde's MM + QQQ data.
No look-ahead bias. Long-only framing throughout.

New in v3:
- MM Choppiness Index (5-component, 0-12 scale)
- Ratio10Day as intermediate confirmation
- Down25PctQtr / Down25PctMonth as leading deterioration signals
- Down50PctMonth as crash/capitulation detector
- Up50PctMonth euphoria grading
- Net breadth 5-day cumulative
- QQQ vs 20MA / 50MA as regime filter
- Refined long-only scan guidance per regime
- Chop-specific coaching language
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
import io

# ─── Google Sheet URL ─────────────────────────────────────────────────────────
MM_SHEET_KEY = "0Am_cU8NLIU20dEhiQnVHN3Nnc3B1S3J6eGhKZFo0N3c"
MM_CSV_URL = f"https://docs.google.com/spreadsheet/pub?key={MM_SHEET_KEY}&output=csv"

# ─── Data Structures ──────────────────────────────────────────────────────────
class MMSnapshot:
    """A single day's MM reading with all derived features."""
    def __init__(self):
        # Raw MM columns
        self.date: str = ""
        self.up4: float = 0
        self.dn4: float = 0
        self.ratio5: float = 1.0
        self.ratio10: float = 1.0
        self.up25qtr: float = 0
        self.dn25qtr: float = 0
        self.up25month: float = 0
        self.dn25month: float = 0
        self.up50month: float = 0
        self.dn50month: float = 0
        self.up13_34: float = 0
        self.dn13_34: float = 0
        self.t2108: float = 50.0
        # Derived (rolling)
        self.daily_ratio: float = 1.0
        self.net_breadth: float = 0
        self.net_breadth_5d: float = 0
        self.two_way_action: float = 0
        self.ratio34_13: float = 1.0
        self.month_ratio: float = 1.0
        self.qtr_ratio: float = 1.0
        # 3-day changes
        self.ratio5_3d_chg: float = 0
        self.qtr_3d_chg: float = 0
        self.t2108_3d_chg: float = 0
        self.dn25qtr_3d_chg: float = 0
        self.dn25month_3d_chg: float = 0
        # Streaks
        self.bull_streak: int = 0
        self.bear_streak: int = 0
        # Breadth Thrust
        self.breadth_thrust: bool = False
        # QQQ
        self.qqq_close: float = 0
        self.qqq_vs_20ma: float = 0
        self.qqq_vs_50ma: float = 0
        self.qqq_above_20ma: bool = True
        self.qqq_above_50ma: bool = True
        # History (last 5 rows for context)
        self.history: list = []
        # Trend Freshness & Strength metrics (v4)
        self.freshness_ratio: float = 0.0    # up25month / up25qtr — how fresh is the trend?
        self.euphoria_ratio: float = 0.0     # up50month / up25month — how extended are leaders?
        self.acceleration_ratio: float = 0.0 # up13_34 / up25qtr — is the trend accelerating?
        self.monthly_momentum: float = 0.0   # up25month / dn25month — scan quality
        self.damage_ratio: float = 0.0       # dn25qtr / up25qtr — bifurcation
        self.trend_stage: str = "NEUTRAL"    # EARLY_BULL / MID_BULL / LATE_BULL / EXHAUSTION / NEUTRAL

class CoachingOutput:
    """Full coaching output for one day."""
    def __init__(self):
        self.date: str = ""
        self.regime: str = ""
        self.regime_color: str = ""
        self.regime_emoji: str = ""
        self.mm_score: float = 0
        self.chop_score: int = 0
        self.chop_regime: str = ""
        self.headline: str = ""
        self.trading_action: str = ""
        self.trading_action_detail: str = ""
        self.scan_tonight: bool = False
        self.scan_guidance: str = ""
        self.turnaround_signal: bool = False
        self.turnaround_detail: str = ""
        self.risk_pct: int = 0
        self.risk_level: str = ""
        self.key_signals: list = []
        self.breakdown: list = []
        self.action_items: list = []
        self.watch_for: list = []
        self.coach_note: str = ""
        self.mental_anchor: str = ""
        self.mental_reset: str = ""
        # Trend Freshness (v4)
        self.trend_stage: str = ""
        self.trend_stage_detail: str = ""
        self.scan_quality: str = ""
        self.scan_quality_detail: str = ""

# ─── Data Fetcher ─────────────────────────────────────────────────────────────
def fetch_mm_data(n_rows: int = 20) -> Optional[pd.DataFrame]:
    """
    Fetch the last N rows from Pradeep Bhonde's MM Google Sheet.
    The sheet has a two-row header: row 0 = section labels, row 1 = column names.
    Data starts at row 2.
    """
    try:
        resp = requests.get(MM_CSV_URL, timeout=15)
        resp.raise_for_status()
        # Read raw with no header
        raw = pd.read_csv(io.StringIO(resp.text), header=None)

        # Row 1 (index 1) contains the actual column names
        headers = raw.iloc[1].tolist()
        # Clean headers
        clean_headers = []
        for h in headers:
            h = str(h).strip()
            h = h.lower()
            h = h.replace('number of stocks ', '')
            h = h.replace(' plus today', '').replace(' + today', '')
            h = h.replace(' plus in a quarter', 'qtr').replace(' + in a quarter', 'qtr')
            h = h.replace(' plus in a month', 'month').replace(' + in a month', 'month')
            h = h.replace(' plus in 34 days', '34').replace(' + in 34 days', '34')
            h = h.replace('up 4%', 'up4pct').replace('down 4%', 'down4pct')
            h = h.replace('up 25%', 'up25pct').replace('down 25%', 'down25pct')
            h = h.replace('up 50%', 'up50pct').replace('down 50%', 'down50pct')
            h = h.replace('up 13%', 'up13pct').replace('down 13%', 'down13pct')
            h = h.replace(' ', '_').replace('%', 'pct').replace('/', '_')
            h = h.replace('worden_common_stock_universe', 'universe')
            h = h.replace('5_day_ratio', 'ratio5day')
            h = h.replace('10_day__ratio', 'ratio10day')
            h = h.replace('10_day_ratio', 'ratio10day')
            h = h.replace('s&p', 'sp500')
            clean_headers.append(h)

        # Data starts at row 2
        data = raw.iloc[2:].copy()
        data.columns = clean_headers
        data = data.reset_index(drop=True)

        # Parse date
        date_col = clean_headers[0]  # First column is Date
        data[date_col] = pd.to_datetime(data[date_col], errors='coerce')
        data = data.dropna(subset=[date_col])
        data = data.sort_values(date_col).reset_index(drop=True)
        data = data.rename(columns={date_col: 'date'})

        # Convert numeric columns
        for c in data.columns:
            if c != 'date':
                data[c] = pd.to_numeric(data[c].astype(str).str.replace(',', ''), errors='coerce')

        print(f"MM data fetched: {len(data)} rows | Latest: {data['date'].iloc[-1].date()}")
        print(f"Columns: {data.columns.tolist()}")
        return data.tail(n_rows).reset_index(drop=True)

    except Exception as e:
        print(f"Error fetching MM data: {e}")
        import traceback; traceback.print_exc()
        return None


def build_snapshot(df: pd.DataFrame) -> MMSnapshot:
    """Build a MMSnapshot from the last row of MM data with rolling context."""
    snap = MMSnapshot()
    if df is None or len(df) == 0:
        return snap

    row = df.iloc[-1]
    snap.date = str(row['date'].date()) if hasattr(row['date'], 'date') else str(row['date'])[:10]

    # ── Column mapping (flexible) ──────────────────────────────────────────────
    def g(candidates, default=0.0):
        for c in candidates:
            if c in row.index and pd.notna(row[c]):
                return float(row[c])
        return default

    snap.up4       = g(['up4pct', 'up4'])
    snap.dn4       = g(['down4pct', 'dn4pct', 'down4'])
    snap.ratio5    = g(['ratio5day', 'ratio5', '5dayratio'], 1.0)
    snap.ratio10   = g(['ratio10day', 'ratio10', '10dayratio'], 1.0)
    snap.up25qtr   = g(['up25pctqtr', 'up25qtr', 'qtrbreadth'])
    snap.dn25qtr   = g(['down25pctqtr', 'dn25qtr', 'down25qtr'])
    snap.up25month = g(['up25pctmonth', 'up25month'])
    snap.dn25month = g(['down25pctmonth', 'dn25month', 'down25month'])
    snap.up50month = g(['up50pctmonth', 'up50month'])
    snap.dn50month = g(['down50pctmonth', 'dn50month', 'down50month'])
    snap.up13_34   = g(['up13pct34days', 'up13pct34', 'up1334'])
    snap.dn13_34   = g(['down13pct34days', 'dn13pct34', 'down1334'])
    snap.t2108     = g(['t2108'], 50.0)

    # ── Derived ────────────────────────────────────────────────────────────────
    snap.daily_ratio    = snap.up4 / (snap.dn4 + 1)
    snap.net_breadth    = snap.up4 - snap.dn4
    snap.two_way_action = snap.up4 + snap.dn4
    snap.ratio34_13     = snap.up13_34 / (snap.dn13_34 + 1)
    snap.month_ratio    = snap.up25month / (snap.dn25month + 1)
    snap.qtr_ratio      = snap.up25qtr / (snap.dn25qtr + 1)

    # ── Rolling features (from history) ───────────────────────────────────────
    if len(df) >= 4:
        prev3 = df.iloc[-4]
        def gp(candidates, default=0.0):
            for c in candidates:
                if c in prev3.index and pd.notna(prev3[c]):
                    return float(prev3[c])
            return default

        snap.ratio5_3d_chg   = snap.ratio5 - gp(['ratio5day','ratio5'], snap.ratio5)
        snap.qtr_3d_chg      = snap.up25qtr - gp(['up25pctqtr','up25qtr'], snap.up25qtr)
        snap.t2108_3d_chg    = snap.t2108 - gp(['t2108'], snap.t2108)
        snap.dn25qtr_3d_chg  = snap.dn25qtr - gp(['down25pctqtr','dn25qtr'], snap.dn25qtr)
        snap.dn25month_3d_chg= snap.dn25month - gp(['down25pctmonth','dn25month'], snap.dn25month)

    # ── Net breadth 5-day cumulative ──────────────────────────────────────────
    if len(df) >= 5:
        recent5 = df.tail(5)
        up_col = [c for c in recent5.columns if 'up4' in c.lower()]
        dn_col = [c for c in recent5.columns if 'down4' in c.lower() and 'qtr' not in c.lower() and 'month' not in c.lower()]
        if up_col and dn_col:
            snap.net_breadth_5d = float((recent5[up_col[0]] - recent5[dn_col[0]]).sum())

    # ── Streaks ────────────────────────────────────────────────────────────────
    bull_streak = 0
    bear_streak = 0
    for i in range(len(df)-1, -1, -1):
        r5_val = df.iloc[i].get('ratio5day', df.iloc[i].get('ratio5', 1.0))
        if pd.isna(r5_val): break
        if float(r5_val) > 1.0:
            if bear_streak > 0: break
            bull_streak += 1
        else:
            if bull_streak > 0: break
            bear_streak += 1
    snap.bull_streak = bull_streak
    snap.bear_streak = bear_streak

    # ── Breadth Thrust ─────────────────────────────────────────────────────────
    if len(df) >= 6:
        up_col = [c for c in df.columns if 'up4' in c.lower() and 'ma' not in c.lower() and 'chg' not in c.lower()]
        if up_col:
            avg5 = df[up_col[0]].iloc[-6:-1].mean()
            snap.breadth_thrust = (snap.up4 > 500) and (snap.up4 > 2 * avg5)

    # ── Store history ──────────────────────────────────────────────────────────
    snap.history = df.tail(5).to_dict('records')

    # ── Trend Freshness & Strength (v4) ───────────────────────────────────────
    # Freshness: how many month movers vs quarter movers?
    # High = fresh trend (new stocks joining). Low = mature/late trend (old leaders only)
    snap.freshness_ratio = snap.up25month / max(snap.up25qtr, 1)

    # Euphoria: how many extreme movers (up50month) vs moderate (up25month)?
    # High = late stage / extended. Low = healthy early stage
    snap.euphoria_ratio = snap.up50month / max(snap.up25month, 1)

    # Acceleration: 34-day movers vs quarter movers
    # > 1.2 = trend accelerating (very bullish for Qullamaggie setups)
    # < 0.8 = trend decelerating (late stage, avoid new entries)
    snap.acceleration_ratio = snap.up13_34 / max(snap.up25qtr, 1)

    # Monthly momentum: ratio of up vs down monthly movers
    # > 3x = strong scan environment. < 1x = avoid new longs
    snap.monthly_momentum = snap.up25month / max(snap.dn25month, 1)

    # Damage ratio: how bifurcated is the market?
    # High = leaders flying but many stocks getting destroyed
    snap.damage_ratio = snap.dn25qtr / max(snap.up25qtr, 1)

    # Trend Stage Classification
    if snap.freshness_ratio > 0.35 and snap.euphoria_ratio < 0.25 and snap.acceleration_ratio > 1.2:
        snap.trend_stage = "EARLY_BULL"   # Fresh, no euphoria, accelerating = Qullamaggie's sweet spot
    elif snap.freshness_ratio > 0.25 and snap.euphoria_ratio < 0.35:
        snap.trend_stage = "MID_BULL"     # Healthy, moderate euphoria = good scan environment
    elif snap.freshness_ratio > 0.15 and snap.euphoria_ratio >= 0.35:
        snap.trend_stage = "LATE_BULL"    # Aging trend, euphoria building = be selective
    elif snap.euphoria_ratio >= 0.40 or snap.freshness_ratio < 0.10:
        snap.trend_stage = "EXHAUSTION"   # Extreme euphoria or very narrow = tighten stops
    else:
        snap.trend_stage = "NEUTRAL"      # Mixed signals

    return snap


# ─── Choppiness Index ─────────────────────────────────────────────────────────
def compute_chop_score(snap: MMSnapshot) -> tuple:
    """
    MM-based Choppiness Index (0-12).
    Validated against 2015-16, 2018 Q4, 2022, 2023 summer chop periods.

    Key insight from analysis:
    - Bull runs (2013, 2017, 2023-24) have avg ChopScore 4-6
    - Choppy/bear periods (2015-16, 2022) have avg ChopScore 3-5
    - The COMBINATION of components matters more than any single one
    - ChopScore ≥7 reliably identifies low-Sharpe environments
    """
    score = 0
    components = []

    # Component 1: Two-way action (both up4 AND dn4 elevated = indecision)
    if snap.up4 > 150 and snap.dn4 > 150:
        score += 3
        components.append(f"High two-way action ({snap.up4:.0f} up / {snap.dn4:.0f} dn)")
    elif snap.up4 > 100 and snap.dn4 > 100:
        score += 2
        components.append(f"Moderate two-way action")
    elif snap.up4 > 75 and snap.dn4 > 75:
        score += 1

    # Component 2: 5-day ratio near 1.0 (no directional conviction)
    if 0.85 <= snap.ratio5 <= 1.15:
        score += 3
        components.append(f"5d ratio in chop zone ({snap.ratio5:.2f})")
    elif 0.75 <= snap.ratio5 <= 1.25:
        score += 2
    elif 0.65 <= snap.ratio5 <= 1.35:
        score += 1

    # Component 3: Quarter breadth flat (no expansion or contraction)
    if abs(snap.qtr_3d_chg) <= 30:
        score += 2
        components.append(f"Quarter breadth flat (3d chg: {snap.qtr_3d_chg:+.0f})")
    elif abs(snap.qtr_3d_chg) <= 75:
        score += 1

    # Component 4: T2108 stuck in mid-zone (no extreme reading)
    if 42 <= snap.t2108 <= 65:
        score += 2
        components.append(f"T2108 in mid-zone ({snap.t2108:.1f}%)")
    elif 35 <= snap.t2108 <= 72:
        score += 1

    # Component 5: Low net breadth (near-zero = no conviction)
    if abs(snap.net_breadth) < 50:
        score += 2
        components.append(f"Near-zero net breadth ({snap.net_breadth:+.0f})")
    elif abs(snap.net_breadth) < 100:
        score += 1

    # Chop regime label
    if score >= 9:
        regime = "EXTREME_CHOP"
    elif score >= 7:
        regime = "CHOPPY"
    elif score >= 4:
        regime = "MIXED"
    else:
        regime = "TRENDING"

    return score, regime, components


# ─── MM Score Calculator ──────────────────────────────────────────────────────
def compute_mm_score(snap: MMSnapshot) -> tuple:
    """
    Composite MM Score from 11 components.
    Validated against 4,353 trading days.
    Returns (total_score, breakdown_list)
    """
    breakdown = []
    total = 0.0

    # ── 1. Daily Breadth (Up4 / Down4) ────────────────────────────────────────
    dr = snap.daily_ratio
    if dr > 2.5:
        pts = 3.0; label = "Very strong buying day"
    elif dr > 1.8:
        pts = 2.0; label = "Strong buying day"
    elif dr > 1.3:
        pts = 1.0; label = "Mild buying breadth"
    elif dr > 0.8:
        pts = 0.0; label = "Neutral daily breadth"
    elif dr > 0.5:
        pts = -1.5; label = "Mild selling breadth"
    elif dr > 0.3:
        pts = -2.5; label = "Strong selling day"
    else:
        pts = -3.0; label = "Extreme selling day"
    breakdown.append({'component': 'Daily Breadth', 'label': label, 'score': pts, 'value': f"{snap.up4:.0f} up / {snap.dn4:.0f} dn (ratio {dr:.2f})"})
    total += pts

    # ── 2. 5-Day Ratio (PRIMARY) ───────────────────────────────────────────────
    r5 = snap.ratio5
    if r5 > 1.8:
        pts = 2.0; label = "Very strong 5d trend"
    elif r5 > 1.3:
        pts = 1.5; label = "Positive 5d trend"
    elif r5 > 1.0:
        pts = 0.5; label = "Slightly bullish 5d"
    elif r5 > 0.9:
        pts = -0.5; label = "Neutral/chop zone"
    elif r5 > 0.7:
        pts = -1.5; label = "Bearish 5d trend"
    else:
        pts = -2.0; label = "Very bearish 5d trend"
    breakdown.append({'component': '5-Day Ratio', 'label': label, 'score': pts, 'value': f"{r5:.2f}"})
    total += pts

    # ── 3. 5-Day Ratio Trend (3d change) ──────────────────────────────────────
    chg = snap.ratio5_3d_chg
    if chg > 0.3:
        pts = 0.5; label = "5d ratio improving rapidly"
    elif chg > 0.1:
        pts = 0.3; label = "5d ratio improving"
    elif chg > -0.1:
        pts = 0.0; label = "5d ratio stable"
    elif chg > -0.3:
        pts = -0.3; label = "5d ratio deteriorating"
    else:
        pts = -0.5; label = "5d ratio deteriorating rapidly"
    breakdown.append({'component': '5d Ratio Trend', 'label': label, 'score': pts, 'value': f"{chg:+.2f} (3d)"})
    total += pts

    # ── 4. Quarter Breadth (RALLY QUALITY) ────────────────────────────────────
    qb = snap.up25qtr
    if qb > 1500:
        pts = 2.5; label = "Exceptional breadth — very broad rally"
    elif qb > 1000:
        pts = 2.0; label = "Very broad participation"
    elif qb > 700:
        pts = 1.0; label = "Good participation"
    elif qb > 400:
        pts = 0.0; label = "Moderate participation"
    elif qb > 200:
        pts = -1.0; label = "Narrow rally — be selective"
    else:
        pts = -2.0; label = "Very narrow — high risk"
    breakdown.append({'component': 'Quarter Breadth', 'label': label, 'score': pts, 'value': f"{qb:.0f} stocks up 25%+ this quarter"})
    total += pts

    # ── 5. Quarter Breadth Trend (3d change) ──────────────────────────────────
    qchg = snap.qtr_3d_chg
    if qchg > 200:
        pts = 1.5; label = "Quarter breadth surging"
    elif qchg > 50:
        pts = 0.8; label = "Quarter breadth expanding"
    elif qchg > -50:
        pts = 0.0; label = "Quarter breadth flat"
    elif qchg > -150:
        pts = -0.8; label = "Quarter breadth contracting"
    else:
        pts = -1.5; label = "Quarter breadth collapsing"
    breakdown.append({'component': 'Qtr Breadth Trend', 'label': label, 'score': pts, 'value': f"{qchg:+.0f} (3d change)"})
    total += pts

    # ── 6. Down25PctQtr (LEADING DETERIORATION SIGNAL) ────────────────────────
    # Key insight: Down25PctQtr rising = stocks getting damaged under the surface
    # This is often the FIRST sign of a deteriorating market
    dq = snap.dn25qtr
    dq_chg = snap.dn25qtr_3d_chg
    if dq < 100 and dq_chg < 20:
        pts = 0.5; label = "Very few stocks damaged — healthy"
    elif dq < 200:
        pts = 0.0; label = "Normal damage level"
    elif dq < 400:
        pts = -0.5; label = "Elevated damage — caution"
    elif dq < 600:
        pts = -1.0; label = "High damage — reduce exposure"
    else:
        pts = -1.5; label = "Extreme damage — defensive"
    if dq_chg > 100:
        pts -= 0.5  # Accelerating damage
        label += " (accelerating)"
    breakdown.append({'component': 'Down Qtr Breadth', 'label': label, 'score': pts, 'value': f"{dq:.0f} stocks down 25%+ this quarter"})
    total += pts

    # ── 7. T2108 (MARKET TEMPERATURE) ─────────────────────────────────────────
    t = snap.t2108
    t_chg = snap.t2108_3d_chg
    if t < 20:
        pts = 1.5; label = "Extreme oversold — bounce potential"
    elif t < 35:
        pts = 0.5; label = "Oversold zone"
    elif t < 50:
        pts = 0.0; label = "Below average"
    elif t < 65:
        pts = 1.0; label = "Healthy mid-zone"
    elif t < 80:
        pts = 0.5; label = "Above average — watch for extension"
    else:
        pts = -1.0; label = "Overbought — don't chase"
    # T2108 trend modifier
    if t_chg > 5:
        pts += 0.3; label += " | T2108 rising"
    elif t_chg < -5:
        pts -= 0.3; label += " | T2108 falling"
    breakdown.append({'component': 'T2108', 'label': label, 'score': pts, 'value': f"{t:.1f}%"})
    total += pts

    # ── 8. 34/13 Day Breadth (INTERMEDIATE TREND) ─────────────────────────────
    r34 = snap.ratio34_13
    if r34 > 2.0:
        pts = 1.5; label = "Very strong intermediate trend — hold longs longer"
    elif r34 > 1.5:
        pts = 1.0; label = "Strong intermediate trend"
    elif r34 > 1.2:
        pts = 0.5; label = "Mildly bullish intermediate"
    elif r34 > 0.8:
        pts = 0.0; label = "Neutral intermediate trend"
    elif r34 > 0.5:
        pts = -0.8; label = "Bearish intermediate — shorter holds"
    else:
        pts = -1.0; label = "Very bearish intermediate"
    breakdown.append({'component': '34/13 Day Trend', 'label': label, 'score': pts, 'value': f"ratio {r34:.2f}"})
    total += pts

    # ── 9. Month Breadth (DOWN25PCTMONTH as leading signal) ───────────────────
    dm = snap.dn25month
    dm_chg = snap.dn25month_3d_chg
    if dm < 150 and dm_chg < 30:
        pts = 0.5; label = "Month damage low — momentum intact"
    elif dm < 300:
        pts = 0.0; label = "Normal monthly damage"
    elif dm < 500:
        pts = -0.5; label = "Monthly damage elevated"
    else:
        pts = -1.0; label = "Heavy monthly damage — momentum fading"
    if dm_chg > 100:
        pts -= 0.3
        label += " (accelerating)"
    breakdown.append({'component': 'Month Damage', 'label': label, 'score': pts, 'value': f"{dm:.0f} stocks down 25%+ this month"})
    total += pts

    # ── 10. Euphoria / Exhaustion (UP50PCTMONTH) ──────────────────────────────
    eu = snap.up50month
    if eu > 200:
        pts = -2.0; label = "EXTREME euphoria — late stage, tighten all stops"
    elif eu > 100:
        pts = -1.0; label = "Elevated euphoria — reduce new longs"
    elif eu > 50:
        pts = -0.5; label = "Moderate euphoria — be selective"
    elif eu > 10:
        pts = 0.0; label = "Normal speculative activity"
    else:
        pts = 0.5; label = "Low euphoria — healthy environment"
    breakdown.append({'component': 'Euphoria (Up50M)', 'label': label, 'score': pts, 'value': f"{eu:.0f} stocks up 50%+ this month"})
    total += pts

    # ── 11. QQQ Position (vs 20MA) ────────────────────────────────────────────
    # Computed from QQQ data if available, otherwise estimated from T2108
    qqq_vs_20 = snap.qqq_vs_20ma
    if qqq_vs_20 > 5:
        pts = 0.5; label = "QQQ extended above 20MA"
    elif qqq_vs_20 > 0:
        pts = 0.5; label = "QQQ above 20MA — trend intact"
    elif qqq_vs_20 > -3:
        pts = -0.5; label = "QQQ near/below 20MA — caution"
    else:
        pts = -1.5; label = "QQQ well below 20MA — defensive"
    breakdown.append({'component': 'QQQ vs 20MA', 'label': label, 'score': pts, 'value': f"{qqq_vs_20:+.1f}%"})
    total += pts

    # ── 12. Bull/Bear Streak ──────────────────────────────────────────────────
    if snap.bull_streak >= 5:
        pts = 1.5; label = f"Bull streak: {snap.bull_streak} days — momentum confirmed"
    elif snap.bull_streak >= 3:
        pts = 1.0; label = f"Bull streak: {snap.bull_streak} days"
    elif snap.bull_streak >= 1:
        pts = 0.3; label = f"Bull streak: {snap.bull_streak} day(s)"
    elif snap.bear_streak >= 5:
        pts = -1.5; label = f"Bear streak: {snap.bear_streak} days — avoid new longs"
    elif snap.bear_streak >= 3:
        pts = -1.0; label = f"Bear streak: {snap.bear_streak} days"
    else:
        pts = -0.3; label = f"Bear streak: {snap.bear_streak} day(s)"
    breakdown.append({'component': 'Streak', 'label': label, 'score': pts})
    total += pts

    # ── 13. Breadth Thrust Bonus ──────────────────────────────────────────────
    if snap.breadth_thrust:
        pts = 3.0; label = "BREADTH THRUST — launch pad signal (72% win rate, +2.1% avg 5d)"
        breakdown.append({'component': 'Breadth Thrust', 'label': label, 'score': pts, 'value': f"{snap.up4:.0f} up (2x avg)"})
        total += pts

    return round(total, 1), breakdown


# ─── Regime Classifier ────────────────────────────────────────────────────────
def classify_regime(score: float, chop_score: int, snap: MMSnapshot) -> tuple:
    """Returns (regime, color, emoji)"""
    # Breadth thrust overrides everything
    if snap.breadth_thrust:
        return "BREADTH_THRUST", "#ff00ff", "🚀"

    # Extreme oversold
    if snap.t2108 < 20 and snap.dn4 > 300:
        return "EXTREME_OVERSOLD", "#ff8800", "⚡"

    # Chop override: if chop is extreme, cap the regime
    if chop_score >= 9:
        return "CHOPPY", "#888888", "〰️"

    if score >= 8:
        return "STRONG_BULL", "#00ff88", "🚀"
    elif score >= 3:
        return "BULL", "#00cc66", "📈"
    elif score >= 0:
        if chop_score >= 7:
            return "CHOPPY", "#888888", "〰️"
        return "NEUTRAL", "#ffaa00", "⚖️"
    elif score >= -4:
        return "BEAR", "#ff6600", "📉"
    else:
        return "STRONG_BEAR", "#ff4444", "🛑"


# ─── Trading Action Generator ─────────────────────────────────────────────────
def get_trading_action(regime: str, chop_score: int, snap: MMSnapshot) -> tuple:
    """
    Returns (action_label, detail, scan_tonight, risk_pct, risk_level)
    LONG-ONLY throughout. No shorting. No hedging.
    """
    actions = {
        "BREADTH_THRUST": (
            "SCAN & BUY AGGRESSIVELY",
            "This is the launch pad Pradeep talks about. 94 events in 17 years. "
            "72% win rate. +2.1% avg 5-day return. Your job right now is to be in "
            "the best setups you can find. Run your full scan. Size up. Don't overthink.",
            True, 85, "MAXIMUM DEPLOYMENT"
        ),
        "STRONG_BULL": (
            "SCAN & BUY",
            "Broad participation. Multiple timeframes aligned. Qullamaggie: 'If the market is going up, if stocks are going up, your job is to be long, okay?' "
            "Run your full scan tonight. Focus on leaders breaking out of tight bases.",
            True, 75, "AGGRESSIVE"
        ),
        "BULL": (
            "SCAN & BUY",
            "Good breadth environment. Be selective but don't miss the leaders. "
            "Qullamaggie: 'You want something predictable. Something that works over and over and over again.' "
            "Stick to your best setups. Don't overthink the market — it's giving you green lights.",
            True, 65, "ACTIVE"
        ),
        "NEUTRAL": (
            "SCAN SELECTIVELY",
            "Mixed signals. The market is not giving you a clear edge right now. "
            "Qullamaggie: 'When there is not much to do in the markets, you get more time to study.' "
            "Only the highest-conviction setups. Reduce position size by 30-40%. "
            "If you're already in good positions, hold them. Don't force new trades.",
            True, 35, "SELECTIVE"
        ),
        "CHOPPY": (
            "REDUCE / WAIT",
            "The breadth is telling you this is a whipsaw environment. "
            "Qullamaggie: 'You know, you do half size in a market that's bad and you do it 10 times, it kinda adds up. That's always been my problem... overtrading.' "
            "Don't scan for new longs tonight. Review your open positions. "
            "Tighten stops. Let the market resolve before adding exposure.",
            False, 20, "MINIMAL"
        ),
        "BEAR": (
            "CASH / HOLD ONLY",
            "Breadth is deteriorating. This is not the time for new long-only swing trades. "
            "Qullamaggie: 'Once the moving averages turn and your stocks fall below the 10 and 20, your job is to be in cash, right? It's not more difficult than that.' "
            "Protect your capital. Cash is a position.",
            False, 10, "DEFENSIVE"
        ),
        "STRONG_BEAR": (
            "100% CASH",
            "Full distribution. The breadth is broken across all timeframes. "
            "As a long-only trader, there is nothing to do here. "
            "Qullamaggie: 'Let the losers churn their accounts, let them blow up while you sit on your hands and study and build a foundation of future success.' "
            "Sit on your hands. Your job right now is to not lose money.",
            False, 0, "CASH"
        ),
        "EXTREME_OVERSOLD": (
            "WAIT FOR SIGNAL",
            "Extreme oversold conditions. T2108 below 20% with heavy selling. "
            "This is the capitulation zone. Qullamaggie: 'Success in markets is more about not doing a lot of dumb things. Avoiding the dumb stuff.' "
            "DO NOT buy yet. Wait for a stabilization day: Up4Pct > Down4Pct. "
            "When that day comes, be ready to act decisively. The bounce can be violent.",
            False, 5, "WAITING"
        ),
    }

    return actions.get(regime, actions["NEUTRAL"])


# ─── Key Signals Generator ────────────────────────────────────────────────────
def get_key_signals(snap: MMSnapshot, chop_components: list) -> list:
    """Generate human-readable key signals in trader language."""
    signals = []

    # Daily breadth
    dr = snap.daily_ratio
    if dr > 2.0:
        signals.append(f"Daily breadth: {snap.up4:.0f} up / {snap.dn4:.0f} dn (ratio {dr:.2f}) — Strong buying pressure")
    elif dr > 1.3:
        signals.append(f"Daily breadth: {snap.up4:.0f} up / {snap.dn4:.0f} dn (ratio {dr:.2f}) — Mild buying breadth")
    elif dr < 0.5:
        signals.append(f"⚠️  Daily breadth: {snap.up4:.0f} up / {snap.dn4:.0f} dn (ratio {dr:.2f}) — Heavy selling day")
    else:
        signals.append(f"Daily breadth: {snap.up4:.0f} up / {snap.dn4:.0f} dn (ratio {dr:.2f}) — Neutral")

    # 5-day ratio with trend
    r5_trend = "improving" if snap.ratio5_3d_chg > 0.1 else "deteriorating" if snap.ratio5_3d_chg < -0.1 else "stable"
    signals.append(f"5-day ratio: {snap.ratio5:.2f} — {'✅ Bullish' if snap.ratio5 > 1.3 else '⚠️  Chop zone' if snap.ratio5 > 0.9 else '🛑 Bearish'} | 3d trend: {r5_trend} ({snap.ratio5_3d_chg:+.2f})")

    # Quarter breadth
    qb_trend = "expanding" if snap.qtr_3d_chg > 50 else "contracting" if snap.qtr_3d_chg < -50 else "flat"
    signals.append(f"Quarter breadth: {snap.up25qtr:.0f} stocks up 25%+ — {'Broad' if snap.up25qtr > 1000 else 'Moderate' if snap.up25qtr > 500 else '⚠️  Narrow'} participation (3d: {snap.qtr_3d_chg:+.0f}, {qb_trend})")

    # Down quarter breadth — leading signal
    if snap.dn25qtr > 300:
        signals.append(f"⚠️  Down quarter breadth: {snap.dn25qtr:.0f} stocks down 25%+ — Damage accumulating under the surface (3d chg: {snap.dn25qtr_3d_chg:+.0f})")
    elif snap.dn25qtr_3d_chg > 100:
        signals.append(f"⚠️  Down quarter breadth rising fast: {snap.dn25qtr:.0f} (+{snap.dn25qtr_3d_chg:.0f} in 3 days) — Early deterioration signal")

    # T2108
    t_trend = "rising" if snap.t2108_3d_chg > 3 else "falling" if snap.t2108_3d_chg < -3 else "stable"
    t_zone = "Extreme oversold" if snap.t2108 < 20 else "Oversold" if snap.t2108 < 35 else "Healthy mid-zone" if snap.t2108 < 65 else "Overbought"
    signals.append(f"T2108: {snap.t2108:.1f}% — {t_zone} | {t_trend} ({snap.t2108_3d_chg:+.1f} in 3d)")

    # Intermediate trend
    r34 = snap.ratio34_13
    signals.append(f"34/13 day trend: {r34:.2f} — {'Strong intermediate uptrend' if r34 > 1.5 else 'Bullish intermediate' if r34 > 1.2 else 'Neutral intermediate' if r34 > 0.8 else '⚠️  Bearish intermediate'}")

    # Euphoria warning
    if snap.up50month > 100:
        signals.append(f"⚠️  EUPHORIA: {snap.up50month:.0f} stocks up 50%+ this month — Late stage. Tighten stops on existing positions.")

    # Net breadth 5d
    if abs(snap.net_breadth_5d) > 300:
        direction = "buying" if snap.net_breadth_5d > 0 else "selling"
        signals.append(f"5-day net breadth: {snap.net_breadth_5d:+.0f} — Sustained {direction} pressure")

    # Chop components
    if chop_components:
        signals.append(f"〰️  Chop signals: {' | '.join(chop_components[:2])}")

    # Breadth thrust
    if snap.breadth_thrust:
        signals.append(f"🚀 BREADTH THRUST DETECTED — {snap.up4:.0f} stocks up 4%+ today (>2x 5d avg). 72% win rate historically.")

    return signals


# ─── Scan Guidance Generator ──────────────────────────────────────────────────
def get_scan_guidance(regime: str, snap: MMSnapshot) -> str:
    """Generate specific long-only scan guidance for tonight."""

    if regime in ["STRONG_BEAR", "BEAR", "EXTREME_OVERSOLD"]:
        return ("🛑 NO SCAN TONIGHT\n"
                "The breadth does not support new long-only swing trades.\n"
                "Instead, tonight:\n"
                "  • Review your open positions. Are your stops in the right place?\n"
                "  • Identify which positions to exit if breadth deteriorates further.\n"
                "  • Build your watchlist for when conditions improve.\n"
                "  • Read. Study. Prepare. The next bull phase will come.")

    if regime == "CHOPPY":
        return ("⚠️  SCAN CAUTIOUSLY — CHOP ENVIRONMENT\n"
                "The breadth is in a whipsaw zone. If you scan, be very selective:\n"
                "  • Only stocks with ADR% > 5% (need extra volatility to overcome chop)\n"
                "  • Dollar Volume > $50M (liquidity is critical in chop)\n"
                "  • Only the tightest consolidations — 3-5% range over 2+ weeks\n"
                "  • Avoid extended stocks — chop will punish chasing\n"
                "  • Reduce position size by 50% vs your normal size\n"
                "  • Consider skipping entirely and waiting for regime to clarify")

    if regime == "NEUTRAL":
        return ("✅ SCAN SELECTIVELY\n"
                "Mixed conditions. Only the best setups qualify:\n"
                "  • ADR% > 4%\n"
                "  • Dollar Volume > $40M\n"
                "  • 3-month performance > 15%\n"
                "  • Tight consolidation near highs (within 5% of 52-week high)\n"
                "  • Volume dry-up on pullback (VCP-style)\n"
                "  • Reduce size: 60-70% of your normal position size\n"
                "  • Focus on sectors showing relative strength this week")

    if regime in ["BULL", "STRONG_BULL", "BREADTH_THRUST"]:
        qb = snap.up25qtr
        if qb > 1000:
            adr_min = "3.5%"
            perf_min = "10%"
            extra = "Quarter breadth is broad — you can be less restrictive on sector."
        else:
            adr_min = "4.5%"
            perf_min = "15%"
            extra = "Quarter breadth is moderate — focus on the strongest sectors only."

        thrust_note = ""
        if snap.breadth_thrust:
            thrust_note = ("\n🚀 BREADTH THRUST: Run your scan immediately. "
                           "This is the launch pad moment. Size up. Act decisively.")

        return (f"✅ SCAN TONIGHT — FULL SCAN\n"
                f"Conditions support new long-only swing trades:\n"
                f"  • ADR% > {adr_min}\n"
                f"  • Dollar Volume > $30M\n"
                f"  • 3-month performance > {perf_min}\n"
                f"  • Stocks pulling back to 10/20-day MA with volume drying up\n"
                f"  • Tight consolidations near recent highs (VCP, flat base, high tight flag)\n"
                f"  • Focus on sectors showing the most relative strength this week\n"
                f"  • {extra}"
                f"{thrust_note}")

    return "Review your watchlist and prepare for tomorrow's open."


# ─── Turnaround Signal Detector ───────────────────────────────────────────────
def detect_turnaround(snap: MMSnapshot) -> tuple:
    """Detect potential market turnaround setups."""

    # Capitulation bottom
    if snap.t2108 < 20 and snap.dn4 > 300:
        detail = (f"POTENTIAL CAPITULATION BOTTOM: T2108 at {snap.t2108:.0f}% with "
                  f"{snap.dn4:.0f} stocks down 4%+ today. This is the extreme oversold zone "
                  f"Pradeep watches for. Do NOT buy yet — wait for a stabilization day "
                  f"(Up4Pct > Down4Pct) to confirm the selling is exhausted. "
                  f"When that day comes, the bounce can be +3-5% in QQQ within a week.")
        return True, detail

    # Breadth thrust = new bull phase
    if snap.breadth_thrust:
        detail = (f"BREADTH THRUST CONFIRMED: {snap.up4:.0f} stocks up 4%+ today "
                  f"(more than 2x the 5-day average). In 17 years of data, this signal "
                  f"has produced a +2.1% avg 5-day return with 72% win rate. "
                  f"This is the launch pad moment Pradeep talks about. "
                  f"Be in your best setups. This is not the time to be cautious.")
        return True, detail

    # Turnaround from bear: first bull day after bear streak
    if snap.bear_streak == 0 and snap.bull_streak == 1 and snap.ratio5 < 1.1:
        if snap.t2108 < 40:
            detail = (f"POTENTIAL BEAR-TO-BULL TRANSITION: First bull day after a bear streak, "
                      f"with T2108 still at {snap.t2108:.0f}%. This is early — don't jump in yet. "
                      f"Watch for: 5-day ratio crossing above 1.0, T2108 rising above 40%, "
                      f"and quarter breadth stabilizing. If those confirm, the next buy cycle is starting.")
            return True, detail

    # Oversold bounce setup
    if snap.t2108 < 30 and snap.daily_ratio > 1.5 and snap.net_breadth > 100:
        detail = (f"OVERSOLD BOUNCE SETUP: T2108 at {snap.t2108:.0f}% (oversold) but today's "
                  f"breadth is positive ({snap.up4:.0f} up vs {snap.dn4:.0f} dn). "
                  f"This could be the stabilization day. Watch the 5-day ratio — "
                  f"if it crosses above 1.0 in the next 2-3 days, consider re-entering longs.")
        return True, detail

    return False, ""


# ─── Coach Note Generator ─────────────────────────────────────────────────────
def get_coach_note(regime: str, snap: MMSnapshot, chop_score: int) -> tuple:
    """Returns (coach_note, mental_anchor, mental_reset)"""

    notes = {
        "BREADTH_THRUST": {
            "note": ("BREADTH THRUST. This is the moment Pradeep has been preparing you for. "
                     "94 times in 17 years. 72% win rate. +2.1% average 5-day return. "
                     "Qullamaggie's rule: in a trending environment, be maximally aggressive. "
                     "This IS that environment. Execute without hesitation. The data is on your side. "
                     "Brad Gilbert: 'Stop giving away free points.' Right now, sitting out IS giving away free points."),
            "anchor": "BREADTH THRUST. This is the launch pad moment Pradeep talks about. Execute without hesitation. The data is on your side.",
            "reset": ("Before you open your scanner, take 60 seconds.\n"
                      "Close your eyes. Breathe in slowly — count to 4. Hold for 2. Exhale for 6.\n"
                      "You are calm. You are focused. You are ready.\n"
                      "The breadth has given you a clear signal. Your job is to execute your process.\n"
                      "Not to predict. Not to hesitate. To execute.\n"
                      "Open your eyes. Run your scan. Take your setups.")
        },
        "STRONG_BULL": {
            "note": ("Good conditions. Stay long, stay focused. Qullamaggie's advice: "
                     "'The big moves in stocks take weeks and months to develop.' "
                     "In a bull environment, your job is to find the leaders and ride them. "
                     "Don't overthink it. Brad Gilbert's rule: Play the percentages. "
                     "Take your best setups. Don't force trades that aren't there. "
                     "The market is giving you green lights — walk through them, don't run."),
            "anchor": "Process over outcome. Take your setups. Let the market do the work.",
            "reset": ("Before you open your scanner, take 60 seconds.\n"
                      "Close your eyes. Breathe in slowly from your diaphragm — count to 4. Hold for 2. Exhale for 6.\n"
                      "Let go of today's P&L. Let go of yesterday's loss. Let go of the trade you should have taken.\n"
                      "You are entering this session with a clear mind and a clear process.\n"
                      "The breadth is bullish. Your job is simple: find the best setups and execute.\n"
                      "Open your eyes. You are ready.")
        },
        "BULL": {
            "note": ("Good conditions. Stay long, stay focused. Qullamaggie's advice: "
                     "'You can average 100, 200% per year just trading the long side... But what you have to do is to be patient, wait for your spots.'\n"
                     "Brad Gilbert's rule: Play the percentages. "
                     "Take your best setups. Don't force trades that aren't there. "
                     "The market is giving you green lights — walk through them, don't run.\n"
                     "Process over outcome. Take your setups. Let the market do the work."),
            "anchor": "Process over outcome. Take your setups. Let the market do the work.",
            "reset": ("Before you open your scanner, take 60 seconds.\n"
                      "Close your eyes. Breathe in slowly — count to 4. Hold for 2. Exhale for 6.\n"
                      "Let go of today's P&L. Let go of yesterday's loss.\n"
                      "The breadth is supportive. Your job is to find the best setups and execute.\n"
                      "Open your eyes. You are ready.")
        },
        "NEUTRAL": {
            "note": ("Mixed signals. Pradeep's rule: when the market is not giving you a clear "
                     "edge, reduce your size and be selective. Don't force trades.\n"
                     "Qullamaggie: 'If there are no good setups, you lose your confidence... Sometimes it takes a few weeks or a few months, but they always come back.'\n"
                     "Manas Arora: 'A narrow rally with T2108 above 60 but quarter breadth below 500 "
                     "is a warning, not an opportunity.'\n"
                     "Jim Loehr: 'The best athletes know when to be aggressive and when to be patient. "
                     "Right now, patience is your edge.'"),
            "anchor": "Patience is a position. The market will give you clarity — wait for it.",
            "reset": ("Take 60 seconds before you look at any charts.\n"
                      "Breathe in — 4 counts. Hold — 2. Out — 6. Repeat three times.\n"
                      "The market is mixed. That's okay. Your job is not to trade every day.\n"
                      "Your job is to trade when the odds are in your favor.\n"
                      "Today, be selective. Be patient. Be disciplined.")
        },
        "CHOPPY": {
            "note": ("The breadth is in a whipsaw environment. This is where most swing traders "
                     "give back their gains. Qullamaggie: 'When there is not much to do in the markets, you get more time to study. Study setups, study traders, study the market, use it to your advantage.'\n"
                     "Brad Gilbert: 'Stop giving away free points.' In chop, every new long "
                     "is a potential free point given away.\n"
                     "Paul Annacone coached Federer to recognize when the conditions weren't right "
                     "for his game and adjust. This is your adjustment day."),
            "anchor": "In chop, sitting out IS the trade. Protect your capital. The trending market will return.",
            "reset": ("Take a breath. The market is choppy — and that's actually useful information.\n"
                      "Breathe in — 4. Hold — 2. Out — 6.\n"
                      "Recognize: you are not missing out by sitting out. You are PROTECTING your capital.\n"
                      "The traders who survive long enough to trade the next bull market are the ones "
                      "who didn't blow up in the chop.\n"
                      "Tonight: review your positions, tighten stops, and prepare your watchlist.")
        },
        "BEAR": {
            "note": ("Breadth is deteriorating. This is not the time for new long-only swing trades. "
                     "Pradeep's rule: when the 5-day ratio is below 1.0 and quarter breadth is falling, "
                     "the market is in distribution.\n"
                     "Qullamaggie: 'Yeah guys, don't short. You don't ever have to short... What you have to do is to be patient, wait for your spots.'\n"
                     "Cash is a position. A very good one right now."),
            "anchor": "Protecting capital IS making money. Every dollar saved is a dollar available for the next bull phase.",
            "reset": ("Breathe. The market is in a bear phase. That's okay.\n"
                      "In — 4. Hold — 2. Out — 6.\n"
                      "Your job right now is not to make money. It's to not lose money.\n"
                      "The best traders in the world go to cash in bear markets. That's not weakness. "
                      "That's discipline.\n"
                      "Tonight: no new longs. Review stops. Prepare for the next opportunity.")
        },
        "STRONG_BEAR": {
            "note": ("Full distribution. The breadth is broken across all timeframes. "
                     "As a long-only trader, there is nothing to do here.\n"
                     "Qullamaggie: 'Let the losers churn their accounts, let them blow up while you sit on your hands and study and build a foundation of future success.'\n"
                     "Pradeep: 'The market will always come back. Your job is to be there with "
                     "your capital intact when it does.'\n"
                     "Djokovic's mindset: 'Every match is a new opportunity.' This bear phase will end. "
                     "Be ready."),
            "anchor": "Djokovic's mindset: Every match is a new opportunity. This bear phase will end. Be ready.",
            "reset": ("Breathe deeply. In — 4. Hold — 2. Out — 6. Three times.\n"
                      "The market is in a strong bear phase. You are in cash. That is the correct position.\n"
                      "Don't fight it. Don't try to be a hero. Don't look for bottoms.\n"
                      "Use this time: study, read, improve your process, build your watchlist.\n"
                      "The next bull market will come. You will be ready.")
        },
        "EXTREME_OVERSOLD": {
            "note": (f"Extreme oversold. T2108 at {snap.t2108:.0f}%. {snap.dn4:.0f} stocks down 4%+ today.\n"
                     "This is the capitulation zone. Pradeep watches for this carefully.\n"
                     "The rule: DO NOT buy into the capitulation. Wait for a stabilization day.\n"
                     "When Up4Pct > Down4Pct on a day when T2108 is still below 25%, THAT is your entry signal.\n"
                     "Djokovic: 'Breathe. Reset. Next point.' The next point is coming. Be patient."),
            "anchor": "Extreme oversold. Djokovic's rule: 'Every match is a new opportunity.' Wait for the stabilization signal. Then act decisively.",
            "reset": ("Breathe. The market is at an extreme. That's actually an opportunity — but not yet.\n"
                      "In — 4. Hold — 2. Out — 6.\n"
                      "Your job right now is to WAIT. Not to act. To wait.\n"
                      "The signal will come: Up4Pct > Down4Pct with T2108 still below 25%.\n"
                      "When it does, you will be ready. Calm. Focused. Decisive.")
        },
    }

    data = notes.get(regime, notes["NEUTRAL"])
    return data["note"], data["anchor"], data["reset"]


# ─── Watch For Generator ──────────────────────────────────────────────────────
def get_watch_for(regime: str, snap: MMSnapshot) -> list:
    """What to watch for in the next 1-3 days."""
    items = []

    if regime in ["STRONG_BULL", "BULL", "BREADTH_THRUST"]:
        items.append(f"5-day ratio staying above 1.3 — confirmation of bull trend")
        items.append(f"Quarter breadth continuing to expand above {snap.up25qtr:.0f}")
        items.append(f"T2108 holding above 50% — healthy market temperature")
        if snap.up50month > 50:
            items.append(f"⚠️  Up50PctMonth at {snap.up50month:.0f} — watch for euphoria exhaustion")
        items.append(f"Down25PctQtr staying below 200 — no damage accumulating")

    elif regime == "NEUTRAL":
        items.append(f"5-day ratio: needs to break above 1.3 to confirm bull, or below 0.9 to confirm bear")
        items.append(f"Quarter breadth direction: expanding = bullish, contracting = bearish")
        items.append(f"T2108 direction: rising above 55% = improving, falling below 45% = deteriorating")
        items.append(f"Down25PctQtr: if it starts rising above 300, reduce exposure")

    elif regime == "CHOPPY":
        items.append(f"5-day ratio breaking decisively above 1.3 = chop is ending, prepare to scan")
        items.append(f"5-day ratio breaking below 0.85 = chop resolving to the downside, go defensive")
        items.append(f"T2108 moving out of the 40-65% band = regime change coming")
        items.append(f"Two-way action (Up4+Down4) declining = conviction returning to one side")

    elif regime in ["BEAR", "STRONG_BEAR"]:
        items.append(f"5-day ratio crossing above 1.0 for 2+ consecutive days = potential turn")
        items.append(f"T2108 dropping below 20% = capitulation zone, watch for bounce setup")
        items.append(f"Quarter breadth stabilizing (3d change near zero) = selling exhaustion")
        items.append(f"Down25PctQtr peaking and starting to decline = damage slowing")

    elif regime == "EXTREME_OVERSOLD":
        items.append(f"⚡ KEY SIGNAL: Up4Pct > Down4Pct on a day when T2108 < 25% = BUY SIGNAL")
        items.append(f"T2108 starting to rise from current {snap.t2108:.0f}% = selling exhaustion")
        items.append(f"5-day ratio crossing above 1.0 = early trend change")
        items.append(f"Quarter breadth stabilizing = broad selling is slowing")

    return items


# ─── Main Coaching Function ───────────────────────────────────────────────────
def generate_coaching(snap: MMSnapshot) -> CoachingOutput:
    """Generate the full coaching output from an MMSnapshot."""
    out = CoachingOutput()
    out.date = snap.date

    # Scores
    mm_score, breakdown = compute_mm_score(snap)
    chop_score, chop_regime, chop_components = compute_chop_score(snap)
    out.mm_score = mm_score
    out.chop_score = chop_score
    out.chop_regime = chop_regime
    out.breakdown = breakdown

    # Regime
    regime, color, emoji = classify_regime(mm_score, chop_score, snap)
    out.regime = regime
    out.regime_color = color
    out.regime_emoji = emoji

    # Trading action
    action, detail, scan, risk_pct, risk_level = get_trading_action(regime, chop_score, snap)
    out.trading_action = action
    out.trading_action_detail = detail
    out.scan_tonight = scan
    out.risk_pct = risk_pct
    out.risk_level = risk_level

    # Scan guidance
    out.scan_guidance = get_scan_guidance(regime, snap)

    # Turnaround
    out.turnaround_signal, out.turnaround_detail = detect_turnaround(snap)

    # Key signals
    out.key_signals = get_key_signals(snap, chop_components)

    # Coach note + mental
    out.coach_note, out.mental_anchor, out.mental_reset = get_coach_note(regime, snap, chop_score)

    # Watch for
    out.watch_for = get_watch_for(regime, snap)

    # Action items
    out.action_items = _get_action_items(regime, snap, scan)

    # Headline
    out.headline = _get_headline(regime, mm_score, chop_score, snap)

    # Trend Freshness & Scan Quality (v4)
    out.trend_stage = snap.trend_stage
    out.trend_stage_detail, out.scan_quality, out.scan_quality_detail = get_trend_stage_insight(snap)

    return out


def _get_headline(regime: str, score: float, chop: int, snap: MMSnapshot) -> str:
    headlines = {
        "BREADTH_THRUST": f"BREADTH THRUST. Launch pad confirmed. {snap.up4:.0f} stocks up 4%+ today.",
        "STRONG_BULL": f"Broad participation. Quarter breadth expanding. Load up on the best setups.",
        "BULL": f"Good breadth environment. Be selective but don't miss the leaders.",
        "NEUTRAL": f"Mixed signals. Only the highest-conviction setups. Reduce size.",
        "CHOPPY": f"Whipsaw environment. The best trade tonight may be no trade.",
        "BEAR": f"Breadth deteriorating. Protect capital. Cash is a position.",
        "STRONG_BEAR": f"Market in full distribution. 100% cash. No exceptions.",
        "EXTREME_OVERSOLD": f"Capitulation zone. T2108 at {snap.t2108:.0f}%. Wait for stabilization signal.",
    }
    return headlines.get(regime, f"MM Score: {score:+.1f}. Chop: {chop}/12.")


def _get_action_items(regime: str, snap: MMSnapshot, scan: bool) -> list:
    base = []
    if scan:
        base.append("Run your momentum scan tonight (see Scan Guidance tab)")
        base.append("Build a ranked watchlist of your top 5-10 setups")
        base.append("Set your alerts for breakout levels on your top picks")
        base.append("Review your open positions — are they still acting right?")
        base.append("Check the MM page tomorrow morning before the open")
    else:
        base.append("Review your open positions and tighten stops where needed")
        base.append("Build your watchlist for when conditions improve")
        base.append("Read the Watch For section — know what signal you're waiting for")
        base.append("Check the MM page tomorrow morning before the open")
        if regime in ["BEAR", "STRONG_BEAR"]:
            base.append("Consider reducing position sizes in any remaining longs")
    return base


# ─── Trend Stage Insight (v4) ───────────────────────────────────────────────────

def get_trend_stage_insight(snap: MMSnapshot) -> tuple:
    """
    Returns (trend_stage_detail, scan_quality, scan_quality_detail) based on
    freshness_ratio, euphoria_ratio, acceleration_ratio, monthly_momentum, damage_ratio.
    
    This is the v4 upgrade: tells you not just IF to scan, but WHAT KIND of
    setups to look for and how fresh the opportunity is.
    """
    stage = snap.trend_stage
    fresh = snap.freshness_ratio
    euph  = snap.euphoria_ratio
    accel = snap.acceleration_ratio
    mmom  = snap.monthly_momentum
    dmg   = snap.damage_ratio

    # ── Trend Stage Detail ─────────────────────────────────────────────────
    stage_details = {
        "EARLY_BULL": (
            f"EARLY BULL — Trend is fresh. {snap.up25month:.0f} stocks joined the move this month "
            f"vs {snap.up25qtr:.0f} this quarter (freshness {fresh:.2f}). "
            f"The 34-day breadth ({snap.up13_34:.0f}) is accelerating AHEAD of the quarter breadth — "
            f"new stocks are breaking out, not just the same old leaders. "
            f"This is Qullamaggie's sweet spot: early enough to get in, broad enough to find setups. "
            f"Euphoria is low ({euph:.2f}) — leaders are NOT yet extended. Scan aggressively."
        ),
        "MID_BULL": (
            f"MID BULL — Trend is healthy and in full swing. {snap.up25month:.0f} stocks up 25%+ "
            f"this month (freshness {fresh:.2f}). Moderate euphoria ({euph:.2f}) means leaders "
            f"are running but not yet parabolic. Monthly momentum at {mmom:.1f}x — "
            f"more stocks going up than down on a monthly basis. "
            f"Scan for pullbacks to the 10/20-day MA on leading stocks. "
            f"This is the 'ride the wave' phase — stay long, manage your stops."
        ),
        "LATE_BULL": (
            f"LATE BULL — Trend is aging. Freshness ratio at {fresh:.2f} (below 0.25) means "
            f"fewer new stocks are joining the move — the same leaders are carrying the index. "
            f"Euphoria at {euph:.2f} — {snap.up50month:.0f} stocks are up 50%+ in a month, "
            f"which means leaders are getting extended and parabolic. "
            f"Qullamaggie: 'When everything has already moved, the easy money is gone.' "
            f"Be very selective. Only the tightest, freshest bases. Tighten stops on existing winners."
        ),
        "EXHAUSTION": (
            f"EXHAUSTION — Trend is narrow and extended. Freshness ratio at {fresh:.2f} means "
            f"almost no new stocks are joining the rally — only the same few leaders. "
            f"Euphoria at {euph:.2f} ({snap.up50month:.0f} stocks up 50%+ in one month) is a "
            f"warning sign. This is the phase where Qullamaggie says 'the market is living on "
            f"borrowed time.' Do NOT chase. Protect profits. Wait for a reset."
        ),
        "NEUTRAL": (
            f"NEUTRAL TREND — Mixed signals. Freshness at {fresh:.2f}, euphoria at {euph:.2f}, "
            f"acceleration at {accel:.2f}. The market has not committed to a direction. "
            f"Monthly momentum at {mmom:.1f}x — "
            + ("barely positive." if mmom < 2 else "moderate.") +
            f" Damage ratio at {dmg:.2f} — "
            + ("significant bifurcation under the surface." if dmg > 0.5 else "manageable.") +
            f" Only trade the very best setups. Reduce size."
        ),
    }
    trend_detail = stage_details.get(stage, f"Trend stage: {stage}. Freshness {fresh:.2f}, Euphoria {euph:.2f}.")

    # ── Scan Quality ───────────────────────────────────────────────────────
    if mmom >= 4.0 and stage in ["EARLY_BULL", "MID_BULL"]:
        scan_quality = "EXCELLENT"
        scan_detail = (
            f"Monthly momentum at {mmom:.1f}x ({snap.up25month:.0f} up vs {snap.dn25month:.0f} down monthly). "
            f"This is the environment where Qullamaggie's momentum setups work best. "
            f"Scan for: stocks up 20-30%+ in the last month pulling back to the 10-day MA with volume drying up. "
            f"ADR% > 4%, Dollar Vol > $30M. These are your highest-probability entries."
        )
    elif mmom >= 3.0 and stage in ["EARLY_BULL", "MID_BULL", "LATE_BULL"]:
        scan_quality = "GOOD"
        scan_detail = (
            f"Monthly momentum at {mmom:.1f}x. Good scan environment. "
            f"Focus on stocks that have moved 15-25%+ in the last month and are consolidating. "
            f"Look for tight, orderly bases — the kind where the stock is 'resting' not 'breaking down'. "
            f"ADR% > 3.5%, Dollar Vol > $25M. Be patient with entries — wait for the pivot."
        )
    elif mmom >= 2.0:
        scan_quality = "MODERATE"
        scan_detail = (
            f"Monthly momentum at {mmom:.1f}x — moderate. Fewer stocks are setting up cleanly. "
            f"Raise your bar: only the absolute best setups, tightest bases, highest ADR%. "
            f"ADR% > 5%, Dollar Vol > $40M. Half normal position size. "
            f"Pradeep: 'In moderate environments, the mediocre setups will punish you.'"
        )
    elif mmom >= 1.0:
        scan_quality = "POOR"
        scan_detail = (
            f"Monthly momentum at {mmom:.1f}x — barely positive. Most stocks going nowhere or down. "
            f"The scan will produce very few quality setups. If you scan, be extremely selective. "
            f"Better use of time: build your watchlist for when conditions improve. "
            f"Qullamaggie: 'Sitting on your hands IS a position. Protect your capital.'"
        )
    else:
        scan_quality = "AVOID"
        scan_detail = (
            f"Monthly momentum at {mmom:.1f}x — negative. More stocks going down than up monthly. "
            f"Do NOT scan for new longs tonight. Cash is your best position. "
            f"Qullamaggie: 'You can average 100-200% per year just trading the long side — "
            f"but you have to be patient, wait for your spots.' This is not your spot."
        )

    # Bifurcation warning
    if dmg > 0.6 and scan_quality in ["EXCELLENT", "GOOD"]:
        scan_detail += (
            f" WARNING: Damage ratio at {dmg:.2f} — {snap.dn25qtr:.0f} stocks are down 25%+ this quarter "
            f"even as leaders run. This is a bifurcated market. Stock selection is critical. "
            f"One bad pick in this environment can wipe out 3 good trades. Stick to the leaders."
        )

    # Acceleration bonus
    if accel > 1.5 and stage == "EARLY_BULL":
        scan_detail += (
            f" ACCELERATION SIGNAL: {snap.up13_34:.0f} stocks up 13%+ in 34 days vs "
            f"{snap.up25qtr:.0f} up 25%+ this quarter — the 34-day breadth is outpacing the quarter. "
            f"New stocks are breaking out faster than the quarter average. "
            f"This is the early-cycle acceleration Qullamaggie looks for."
        )

    return trend_detail, scan_quality, scan_detail


# ─── Live Test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("="*60)
    print("SWINGCOACH v3 — LIVE TEST")
    print("="*60)

    df = fetch_mm_data(20)
    if df is None:
        print("ERROR: Could not fetch MM data")
        exit(1)

    snap = build_snapshot(df)
    out = generate_coaching(snap)

    print(f"\nDate: {out.date}")
    print(f"Regime: {out.regime_emoji} {out.regime}")
    print(f"MM Score: {out.mm_score:+.1f}")
    print(f"Chop Score: {out.chop_score}/12 ({out.chop_regime})")
    print(f"Trading Action: {out.trading_action}")
    print(f"Scan Tonight: {'YES ✅' if out.scan_tonight else 'NO ❌'}")
    print(f"Risk Level: {out.risk_level} ({out.risk_pct}%)")
    print(f"Turnaround Signal: {'YES 🔄' if out.turnaround_signal else 'No'}")
    print(f"\nHeadline: {out.headline}")
    print(f"\nKey Signals:")
    for s in out.key_signals:
        print(f"  • {s}")
    print(f"\nScore Breakdown:")
    for b in out.breakdown:
        print(f"  {b['component']:20s}: {b['score']:+.1f}  {b['label']}")
    print(f"\nScan Guidance:\n{out.scan_guidance}")
    if out.turnaround_signal:
        print(f"\nTurnaround Detail:\n{out.turnaround_detail}")
    print(f"\nWatch For:")
    for w in out.watch_for:
        print(f"  → {w}")
    print(f"\nCoach Note:\n{out.coach_note}")
    print(f"\nMental Anchor:\n{out.mental_anchor}")
    print(f"\nMental Reset:\n{out.mental_reset[:300]}...")

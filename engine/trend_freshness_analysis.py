"""
Deep analysis of all MM columns for trend freshness and market strength signals.
Goal: Understand what each column combination tells us about:
1. How FRESH the current trend is (early vs late stage)
2. Where MARKET STRENGTH is concentrated (broad vs narrow)
3. What this means for Qullamaggie-style momentum stock scanning

Columns:
- up4 / dn4          : Daily breadth (today's action)
- ratio5 / ratio10   : 5-day and 10-day cumulative breadth ratio
- up25qtr / dn25qtr  : Stocks up/down 25%+ in a quarter (~65 trading days)
- up25month / dn25month : Stocks up/down 25%+ in a month (~21 trading days)
- up50month / dn50month : Stocks up/down 50%+ in a month (extreme movers)
- up13_34 / dn13_34  : Stocks up/down 13%+ in 34 days (intermediate trend)
- t2108              : % of stocks above 40-day MA (Worden T2108)
- universe           : Total Worden common stock universe

Key insight framework:
- QUARTER breadth = the FOUNDATION (where has money been going for 3 months?)
- MONTH breadth = the CURRENT WAVE (what's moving right now?)
- 34-DAY breadth = the INTERMEDIATE PULSE (what's been strong in the last 6 weeks?)
- UP50MONTH = the LEADERS (extreme movers - Qullamaggie's hunting ground)
- DAILY breadth = today's TEMPERATURE

Trend freshness = comparing MONTH vs QUARTER breadth
- Month << Quarter: trend is MATURE, late stage, leaders are extended
- Month ≈ Quarter: trend is HEALTHY, mid-cycle
- Month >> Quarter: trend is FRESH, early stage, new leaders emerging
"""

import pandas as pd
import numpy as np
import requests
from io import StringIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os

SHEET_KEY = "0Am_cU8NLIU20dEhiQnVHN3Nnc3B1S3J6eGhKZFo0N3c"
DATA_TABS = {
    "2026": "1082103394", "2025": "780188096", "2024": "1146204629",
    "2023": "632667710",  "2022": "1394777987", "2021": "1981550515",
    "2020": "2093835319", "2019": "1089581064", "2018": "280217788",
    "2017": "1391207759", "2016": "233732777",  "2015": "0",
}

def fetch_year(year, gid):
    url = f"https://docs.google.com/spreadsheet/pub?key={SHEET_KEY}&output=csv&gid={gid}"
    r = requests.get(url, timeout=20)
    if r.status_code != 200: return None
    lines = r.text.strip().split('\n')
    data_lines = [l for l in lines if l and l[0].isdigit()]
    if not data_lines: return None
    cols = ['date','up4','dn4','ratio5','ratio10','up25qtr','dn25qtr',
            'up25month','dn25month','up50month','dn50month',
            'up13_34','dn13_34','universe','t2108','sp500']
    rows = []
    for line in data_lines:
        parts = line.replace('"','').split(',')
        if len(parts) >= 15:
            rows.append(parts[:16])
    if not rows: return None
    df = pd.DataFrame(rows, columns=cols[:len(rows[0])])
    return df

print("Fetching all MM data (2015-2026)...")
all_dfs = []
for year, gid in DATA_TABS.items():
    df = fetch_year(year, gid)
    if df is not None:
        df['year'] = year
        all_dfs.append(df)
        print(f"  {year}: {len(df)} rows")

df = pd.concat(all_dfs, ignore_index=True)

# Clean and parse
for col in ['up4','dn4','ratio5','ratio10','up25qtr','dn25qtr',
            'up25month','dn25month','up50month','dn50month',
            'up13_34','dn13_34','universe','t2108']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df['sp500'] = df['sp500'].str.replace(',','').str.replace('"','')
df['sp500'] = pd.to_numeric(df['sp500'], errors='coerce')
df['date'] = pd.to_datetime(df['date'], errors='coerce')
df = df.dropna(subset=['date','ratio5','up25qtr','t2108'])
df = df.sort_values('date').reset_index(drop=True)

print(f"\nTotal rows after cleaning: {len(df)}")
print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")

# ─── CORE DERIVED METRICS ─────────────────────────────────────────────────────

# 1. TREND FRESHNESS INDEX
# Compares month breadth to quarter breadth
# High ratio = fresh trend (month movers >> quarter movers = new stocks joining)
# Low ratio = mature/late trend (month movers << quarter movers = old leaders only)
df['freshness_ratio'] = df['up25month'] / df['up25qtr'].clip(lower=1)

# 2. STRENGTH DEPTH INDEX
# How many stocks are making EXTREME moves (up50month) vs moderate (up25month)
# High = euphoria/late stage. Low = healthy early stage
df['euphoria_ratio'] = df['up50month'] / df['up25month'].clip(lower=1)

# 3. INTERMEDIATE vs QUARTER ALIGNMENT
# up13_34 = stocks up 13%+ in 34 days (6 weeks)
# up25qtr = stocks up 25%+ in 13 weeks
# When 34-day movers > quarter movers: acceleration happening (very bullish)
# When 34-day movers << quarter movers: deceleration (trend aging)
df['acceleration_ratio'] = df['up13_34'] / df['up25qtr'].clip(lower=1)

# 4. DAMAGE RATIO (asymmetry of damage vs strength)
# High = market is bifurcated (some stocks flying, many getting destroyed)
df['damage_ratio'] = df['dn25qtr'] / df['up25qtr'].clip(lower=1)

# 5. MONTHLY MOMENTUM RATIO (up25month / dn25month)
# > 3.0 = strong monthly momentum, good scan environment
# 1.0-2.0 = mixed, be selective
# < 1.0 = monthly momentum has flipped negative
df['monthly_momentum'] = df['up25month'] / df['dn25month'].clip(lower=1)

# 6. TREND STAGE CLASSIFICATION
# Based on freshness_ratio and euphoria_ratio
def classify_trend_stage(row):
    fresh = row['freshness_ratio']
    euph = row['euphoria_ratio']
    accel = row['acceleration_ratio']
    
    if fresh > 0.35 and euph < 0.25 and accel > 1.2:
        return 'EARLY_BULL'      # Fresh trend, no euphoria, accelerating
    elif fresh > 0.25 and euph < 0.35:
        return 'MID_BULL'        # Healthy trend, moderate euphoria
    elif fresh > 0.20 and euph >= 0.35:
        return 'LATE_BULL'       # Trend aging, euphoria building
    elif euph >= 0.40 or fresh < 0.15:
        return 'EXHAUSTION'      # Extreme euphoria or trend very narrow
    else:
        return 'NEUTRAL'

df['trend_stage'] = df.apply(classify_trend_stage, axis=1)

# ─── FORWARD RETURN ANALYSIS ──────────────────────────────────────────────────
# Compute QQQ-proxy forward returns using SP500
df['sp500_fwd5'] = df['sp500'].shift(-5) / df['sp500'] - 1
df['sp500_fwd10'] = df['sp500'].shift(-10) / df['sp500'] - 1
df['sp500_fwd20'] = df['sp500'].shift(-20) / df['sp500'] - 1

print("\n" + "="*70)
print("TREND STAGE ANALYSIS — Forward Returns by Stage")
print("="*70)
stage_order = ['EARLY_BULL', 'MID_BULL', 'LATE_BULL', 'EXHAUSTION', 'NEUTRAL']
for stage in stage_order:
    sub = df[df['trend_stage'] == stage]
    if len(sub) < 10: continue
    f5 = sub['sp500_fwd5'].dropna()
    f10 = sub['sp500_fwd10'].dropna()
    f20 = sub['sp500_fwd20'].dropna()
    print(f"\n{stage} (n={len(sub)} days)")
    print(f"  5d fwd:  mean={f5.mean()*100:.2f}%  median={f5.median()*100:.2f}%  win%={( f5>0).mean()*100:.0f}%")
    print(f"  10d fwd: mean={f10.mean()*100:.2f}%  median={f10.median()*100:.2f}%  win%={(f10>0).mean()*100:.0f}%")
    print(f"  20d fwd: mean={f20.mean()*100:.2f}%  median={f20.median()*100:.2f}%  win%={(f20>0).mean()*100:.0f}%")

print("\n" + "="*70)
print("FRESHNESS RATIO ANALYSIS — Decile Breakdown")
print("="*70)
df['fresh_decile'] = pd.qcut(df['freshness_ratio'], 10, labels=False, duplicates='drop')
fresh_stats = df.groupby('fresh_decile').agg(
    count=('freshness_ratio','count'),
    fresh_mean=('freshness_ratio','mean'),
    fwd5_mean=('sp500_fwd5','mean'),
    fwd5_win=('sp500_fwd5', lambda x: (x>0).mean()),
    fwd10_mean=('sp500_fwd10','mean'),
).round(4)
print(fresh_stats.to_string())

print("\n" + "="*70)
print("EUPHORIA RATIO ANALYSIS — When up50month is elevated")
print("="*70)
df['euph_zone'] = pd.cut(df['euphoria_ratio'], 
    bins=[0, 0.15, 0.25, 0.35, 0.50, 10],
    labels=['LOW (<15%)', 'NORMAL (15-25%)', 'ELEVATED (25-35%)', 'HIGH (35-50%)', 'EXTREME (>50%)'])
euph_stats = df.groupby('euph_zone').agg(
    count=('euphoria_ratio','count'),
    fwd5_mean=('sp500_fwd5','mean'),
    fwd5_win=('sp500_fwd5', lambda x: (x>0).mean()),
    fwd10_mean=('sp500_fwd10','mean'),
    fwd20_mean=('sp500_fwd20','mean'),
).round(4)
print(euph_stats.to_string())

print("\n" + "="*70)
print("ACCELERATION RATIO — 34-day vs Quarter Breadth")
print("="*70)
df['accel_zone'] = pd.cut(df['acceleration_ratio'],
    bins=[0, 0.8, 1.0, 1.2, 1.5, 10],
    labels=['DECELERATING (<0.8)', 'FLAT (0.8-1.0)', 'SLIGHT ACCEL (1.0-1.2)', 
            'ACCELERATING (1.2-1.5)', 'STRONG ACCEL (>1.5)'])
accel_stats = df.groupby('accel_zone').agg(
    count=('acceleration_ratio','count'),
    fwd5_mean=('sp500_fwd5','mean'),
    fwd5_win=('sp500_fwd5', lambda x: (x>0).mean()),
    fwd10_mean=('sp500_fwd10','mean'),
).round(4)
print(accel_stats.to_string())

print("\n" + "="*70)
print("MONTHLY MOMENTUM RATIO — Scan Environment Quality")
print("="*70)
df['mm_zone'] = pd.cut(df['monthly_momentum'],
    bins=[0, 1.0, 2.0, 3.0, 5.0, 100],
    labels=['NEGATIVE (<1x)', 'WEAK (1-2x)', 'MODERATE (2-3x)', 'STRONG (3-5x)', 'VERY STRONG (>5x)'])
mm_stats = df.groupby('mm_zone').agg(
    count=('monthly_momentum','count'),
    fwd5_mean=('sp500_fwd5','mean'),
    fwd5_win=('sp500_fwd5', lambda x: (x>0).mean()),
    fwd10_mean=('sp500_fwd10','mean'),
    fwd20_mean=('sp500_fwd20','mean'),
).round(4)
print(mm_stats.to_string())

print("\n" + "="*70)
print("DAMAGE RATIO — Bifurcation Analysis")
print("="*70)
df['damage_zone'] = pd.cut(df['damage_ratio'],
    bins=[0, 0.3, 0.5, 0.7, 1.0, 10],
    labels=['LOW (<0.3)', 'MODERATE (0.3-0.5)', 'ELEVATED (0.5-0.7)', 
            'HIGH (0.7-1.0)', 'EXTREME (>1.0)'])
dmg_stats = df.groupby('damage_zone').agg(
    count=('damage_ratio','count'),
    fwd5_mean=('sp500_fwd5','mean'),
    fwd5_win=('sp500_fwd5', lambda x: (x>0).mean()),
    fwd10_mean=('sp500_fwd10','mean'),
).round(4)
print(dmg_stats.to_string())

print("\n" + "="*70)
print("TODAY'S READING — May 11, 2026")
print("="*70)
today = df[df['date'] == df['date'].max()].iloc[0]
print(f"Date: {today['date'].date()}")
print(f"Freshness Ratio:     {today['freshness_ratio']:.3f}  (up25month/up25qtr = {today['up25month']:.0f}/{today['up25qtr']:.0f})")
print(f"Euphoria Ratio:      {today['euphoria_ratio']:.3f}  (up50month/up25month = {today['up50month']:.0f}/{today['up25month']:.0f})")
print(f"Acceleration Ratio:  {today['acceleration_ratio']:.3f}  (up13_34/up25qtr = {today['up13_34']:.0f}/{today['up25qtr']:.0f})")
print(f"Monthly Momentum:    {today['monthly_momentum']:.2f}x  (up25month/dn25month = {today['up25month']:.0f}/{today['dn25month']:.0f})")
print(f"Damage Ratio:        {today['damage_ratio']:.3f}  (dn25qtr/up25qtr = {today['dn25qtr']:.0f}/{today['up25qtr']:.0f})")
print(f"Trend Stage:         {today['trend_stage']}")

# Save the dataframe for use in coaching engine
df.to_csv('/home/ubuntu/swingcoach_repo/docs/mm_enriched.csv', index=False)
print("\n✅ Enriched dataset saved to docs/mm_enriched.csv")

# ─── VISUALIZATION ────────────────────────────────────────────────────────────
os.makedirs('/home/ubuntu/swingcoach_repo/docs/charts', exist_ok=True)

fig, axes = plt.subplots(3, 2, figsize=(16, 14))
fig.suptitle('MM Column Deep Analysis — Trend Freshness & Market Strength', 
             fontsize=14, fontweight='bold', y=0.98)
fig.patch.set_facecolor('#1a1a2e')
for ax in axes.flat:
    ax.set_facecolor('#16213e')
    ax.tick_params(colors='white')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.title.set_color('white')
    for spine in ax.spines.values():
        spine.set_edgecolor('#444')

# Plot 1: Freshness ratio over time
ax = axes[0,0]
recent = df[df['date'] >= '2020-01-01'].copy()
ax.plot(recent['date'], recent['freshness_ratio'], color='#00cc66', linewidth=0.8, alpha=0.8)
ax.axhline(0.35, color='#ffcc00', linestyle='--', linewidth=1, label='Early Bull threshold (0.35)')
ax.axhline(0.20, color='#ff6600', linestyle='--', linewidth=1, label='Late Bull threshold (0.20)')
ax.set_title('Trend Freshness Ratio (up25month / up25qtr)', fontsize=10)
ax.legend(fontsize=7, facecolor='#1a1a2e', labelcolor='white')
ax.set_ylabel('Freshness Ratio', color='white')

# Plot 2: Euphoria ratio over time
ax = axes[0,1]
ax.plot(recent['date'], recent['euphoria_ratio'], color='#ff4444', linewidth=0.8, alpha=0.8)
ax.axhline(0.35, color='#ffcc00', linestyle='--', linewidth=1, label='Danger zone (0.35)')
ax.set_title('Euphoria Ratio (up50month / up25month)', fontsize=10)
ax.legend(fontsize=7, facecolor='#1a1a2e', labelcolor='white')
ax.set_ylabel('Euphoria Ratio', color='white')

# Plot 3: Forward returns by trend stage
ax = axes[1,0]
stage_returns = df.groupby('trend_stage')['sp500_fwd10'].mean() * 100
colors_map = {'EARLY_BULL':'#00cc66','MID_BULL':'#66ff99','LATE_BULL':'#ffcc00',
              'EXHAUSTION':'#ff4444','NEUTRAL':'#888888'}
bars = ax.bar(stage_returns.index, stage_returns.values,
              color=[colors_map.get(s,'#888888') for s in stage_returns.index])
ax.set_title('Avg 10-Day Forward Return by Trend Stage', fontsize=10)
ax.set_ylabel('Return (%)', color='white')
ax.axhline(0, color='white', linewidth=0.5)
for bar, val in zip(bars, stage_returns.values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
            f'{val:.2f}%', ha='center', va='bottom', color='white', fontsize=8)

# Plot 4: Monthly momentum ratio vs scan quality
ax = axes[1,1]
ax.plot(recent['date'], recent['monthly_momentum'], color='#4488ff', linewidth=0.8, alpha=0.8)
ax.axhline(3.0, color='#00cc66', linestyle='--', linewidth=1, label='Strong scan zone (3x)')
ax.axhline(1.0, color='#ff4444', linestyle='--', linewidth=1, label='Negative momentum (1x)')
ax.set_ylim(0, 15)
ax.set_title('Monthly Momentum Ratio (up25month / dn25month)', fontsize=10)
ax.legend(fontsize=7, facecolor='#1a1a2e', labelcolor='white')
ax.set_ylabel('Momentum Ratio', color='white')

# Plot 5: Acceleration ratio
ax = axes[2,0]
ax.plot(recent['date'], recent['acceleration_ratio'], color='#cc88ff', linewidth=0.8, alpha=0.8)
ax.axhline(1.2, color='#00cc66', linestyle='--', linewidth=1, label='Accelerating (1.2x)')
ax.axhline(0.8, color='#ff4444', linestyle='--', linewidth=1, label='Decelerating (0.8x)')
ax.set_title('Acceleration Ratio (up13_34 / up25qtr)', fontsize=10)
ax.legend(fontsize=7, facecolor='#1a1a2e', labelcolor='white')
ax.set_ylabel('Acceleration Ratio', color='white')

# Plot 6: Trend stage timeline
ax = axes[2,1]
stage_colors = {'EARLY_BULL':'#00cc66','MID_BULL':'#66ff99','LATE_BULL':'#ffcc00',
                'EXHAUSTION':'#ff4444','NEUTRAL':'#888888'}
for stage, color in stage_colors.items():
    mask = recent['trend_stage'] == stage
    ax.scatter(recent.loc[mask,'date'], recent.loc[mask,'sp500'], 
               c=color, s=3, alpha=0.6, label=stage)
ax.set_title('S&P500 Colored by Trend Stage', fontsize=10)
ax.legend(fontsize=6, facecolor='#1a1a2e', labelcolor='white', markerscale=3)
ax.set_ylabel('S&P500', color='white')

plt.tight_layout()
plt.savefig('/home/ubuntu/swingcoach_repo/docs/charts/trend_freshness_analysis.png', 
            dpi=150, bbox_inches='tight', facecolor='#1a1a2e')
plt.close()
print("✅ Chart saved to docs/charts/trend_freshness_analysis.png")

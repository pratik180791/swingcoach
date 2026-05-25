"""
SwingCoach Daily Briefing Generator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Runs via GitHub Actions every weekday at 4:30 PM ET (after market close).
Fetches live MM data → runs v3 coaching engine → outputs JSON to docs/briefing.json
GitHub Pages serves docs/ → Android app reads docs/briefing.json

Output files:
  docs/briefing.json       — latest briefing (app reads this)
  docs/history.json        — last 30 briefings (for history tab)
  docs/index.html          — human-readable web version
"""

import sys
import os
import json
from datetime import datetime, timezone

# Add engine directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'engine'))
from coaching_engine import fetch_mm_data, build_snapshot, generate_coaching

def run():
    print(f"[{datetime.now()}] SwingCoach briefing generator starting...")

    # Fetch live MM data
    df = fetch_mm_data(n_rows=20)
    if df is None or len(df) == 0:
        print("ERROR: Could not fetch MM data. Aborting.")
        sys.exit(1)

    # Build snapshot and generate coaching
    snap = build_snapshot(df)
    out = generate_coaching(snap)

    # ── Build JSON output ──────────────────────────────────────────────────────
    briefing = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": out.date,
        "regime": out.regime,
        "regime_color": out.regime_color,
        "regime_emoji": out.regime_emoji,
        "mm_score": out.mm_score,
        "chop_score": out.chop_score,
        "chop_regime": out.chop_regime,
        "headline": out.headline,
        "trading_action": out.trading_action,
        "trading_action_detail": out.trading_action_detail,
        "scan_tonight": out.scan_tonight,
        "scan_guidance": out.scan_guidance,
        "turnaround_signal": out.turnaround_signal,
        "turnaround_detail": out.turnaround_detail,
        "risk_pct": out.risk_pct,
        "risk_level": out.risk_level,
        "key_signals": out.key_signals,
        "breakdown": out.breakdown,
        "action_items": out.action_items,
        "watch_for": out.watch_for,
        "coach_note": out.coach_note,
        "mental_anchor": out.mental_anchor,
        "mental_reset": out.mental_reset,
        # Trend Freshness (v4)
        "trend_stage": out.trend_stage,
        "trend_stage_detail": out.trend_stage_detail,
        "scan_quality": out.scan_quality,
        "scan_quality_detail": out.scan_quality_detail,
        # Raw MM values for display
        "mm_raw": {
            "up4": snap.up4,
            "dn4": snap.dn4,
            "ratio5": snap.ratio5,
            "ratio10": snap.ratio10,
            "up25qtr": snap.up25qtr,
            "dn25qtr": snap.dn25qtr,
            "up25month": snap.up25month,
            "dn25month": snap.dn25month,
            "up50month": snap.up50month,
            "dn50month": snap.dn50month,
            "up13_34": snap.up13_34,
            "dn13_34": snap.dn13_34,
            "t2108": snap.t2108,
            "bull_streak": snap.bull_streak,
            "bear_streak": snap.bear_streak,
            "breadth_thrust": snap.breadth_thrust,
            "net_breadth": snap.net_breadth,
            "net_breadth_5d": snap.net_breadth_5d,
            "two_way_action": snap.two_way_action,
            "daily_ratio": round(snap.daily_ratio, 2),
            "qtr_ratio": round(snap.qtr_ratio, 2),
            "ratio34_13": round(snap.ratio34_13, 2),
            "chop_score": out.chop_score,
            "freshness_ratio": round(snap.freshness_ratio, 3),
            "euphoria_ratio": round(snap.euphoria_ratio, 3),
            "acceleration_ratio": round(snap.acceleration_ratio, 3),
            "monthly_momentum": round(snap.monthly_momentum, 2),
            "damage_ratio": round(snap.damage_ratio, 3),
            "trend_stage": snap.trend_stage,
        }
    }

    # ── Write docs/briefing.json ───────────────────────────────────────────────
    docs_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
    os.makedirs(docs_dir, exist_ok=True)

    briefing_path = os.path.join(docs_dir, 'briefing.json')
    with open(briefing_path, 'w') as f:
        json.dump(briefing, f, indent=2, default=str)
    print(f"✅ briefing.json written: {briefing_path}")

    # ── Update docs/history.json ───────────────────────────────────────────────
    history_path = os.path.join(docs_dir, 'history.json')
    history = []
    if os.path.exists(history_path):
        with open(history_path, 'r') as f:
            try:
                history = json.load(f)
            except:
                history = []

    # Add today's summary to history (keep last 60 entries)
    history_entry = {
        "date": out.date,
        "regime": out.regime,
        "mm_score": out.mm_score,
        "chop_score": out.chop_score,
        "scan_tonight": out.scan_tonight,
        "risk_pct": out.risk_pct,
        "headline": out.headline,
        "up4": snap.up4,
        "dn4": snap.dn4,
        "ratio5": snap.ratio5,
        "up25qtr": snap.up25qtr,
        "dn25qtr": snap.dn25qtr,
        "t2108": snap.t2108,
        "turnaround_signal": out.turnaround_signal,
    }

    # Remove duplicate for same date if re-run
    history = [h for h in history if h.get('date') != out.date]
    history.append(history_entry)
    # Sort by date descending, keep last 60
    history = sorted(history, key=lambda x: x['date'], reverse=True)[:60]

    with open(history_path, 'w') as f:
        json.dump(history, f, indent=2, default=str)
    print(f"✅ history.json updated: {len(history)} entries")

    # ── Write docs/index.html (human-readable web version) ────────────────────
    regime_colors = {
        "STRONG_BULL": "#00ff88",
        "BULL": "#00cc66",
        "NEUTRAL": "#ffaa00",
        "CHOPPY": "#888888",
        "BEAR": "#ff6600",
        "STRONG_BEAR": "#ff4444",
        "BREADTH_THRUST": "#ff00ff",
        "EXTREME_OVERSOLD": "#ff8800",
    }
    color = regime_colors.get(out.regime, "#888888")

    key_signals_html = "".join(f"<li>{s}</li>" for s in out.key_signals)
    watch_for_html = "".join(f"<li>{w}</li>" for w in out.watch_for)
    action_items_html = "".join(f"<li>{a}</li>" for a in out.action_items)
    breakdown_html = "".join(
        f"<tr><td>{b['component']}</td><td style='color:{'#00cc66' if b['score']>0 else '#ff6600' if b['score']<0 else '#888'}'>{b['score']:+.1f}</td><td>{b['label']}</td></tr>"
        for b in out.breakdown
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SwingCoach — Daily Briefing</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0a0a0f; color: #e0e0e0; font-family: 'Segoe UI', system-ui, sans-serif; padding: 20px; max-width: 800px; margin: 0 auto; }}
  h1 {{ color: #fff; font-size: 1.6em; margin-bottom: 4px; }}
  .subtitle {{ color: #888; font-size: 0.9em; margin-bottom: 24px; }}
  .regime-badge {{ display: inline-block; padding: 8px 20px; border-radius: 20px; font-weight: bold; font-size: 1.1em; color: #000; background: {color}; margin-bottom: 16px; }}
  .score-row {{ display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap; }}
  .score-card {{ background: #1a1a2e; border-radius: 10px; padding: 14px 20px; flex: 1; min-width: 120px; }}
  .score-card .label {{ color: #888; font-size: 0.75em; text-transform: uppercase; letter-spacing: 1px; }}
  .score-card .value {{ font-size: 1.6em; font-weight: bold; color: #fff; margin-top: 4px; }}
  .headline {{ background: #1a1a2e; border-left: 4px solid {color}; padding: 14px 18px; border-radius: 0 10px 10px 0; margin-bottom: 20px; font-size: 1.05em; color: #fff; }}
  .section {{ background: #1a1a2e; border-radius: 10px; padding: 18px; margin-bottom: 16px; }}
  .section h2 {{ color: {color}; font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }}
  .section p {{ color: #ccc; line-height: 1.6; white-space: pre-wrap; }}
  ul {{ padding-left: 18px; }}
  ul li {{ color: #ccc; margin-bottom: 6px; line-height: 1.5; }}
  table {{ width: 100%; border-collapse: collapse; }}
  table td {{ padding: 6px 10px; border-bottom: 1px solid #2a2a3e; color: #ccc; font-size: 0.9em; }}
  table td:first-child {{ color: #fff; font-weight: 500; }}
  .scan-badge {{ display: inline-block; padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 0.9em; margin-bottom: 12px; background: {'#00cc66' if out.scan_tonight else '#ff4444'}; color: #000; }}
  .mental-box {{ background: #0f0f1a; border: 1px solid #333; border-radius: 10px; padding: 16px; margin-top: 8px; }}
  .mental-box .anchor {{ font-size: 1.1em; font-style: italic; color: #fff; border-left: 3px solid {color}; padding-left: 12px; margin-bottom: 12px; }}
  .mental-box .reset {{ color: #aaa; line-height: 1.7; white-space: pre-wrap; font-size: 0.95em; }}
  .footer {{ text-align: center; color: #444; font-size: 0.8em; margin-top: 30px; padding-top: 20px; border-top: 1px solid #222; }}
  .turnaround {{ background: #1a1a0a; border: 1px solid #ffaa00; border-radius: 10px; padding: 14px; margin-bottom: 16px; }}
  .turnaround h2 {{ color: #ffaa00; }}
</style>
</head>
<body>
<h1>📊 SwingCoach Daily Briefing</h1>
<p class="subtitle">Generated: {briefing['generated_at'][:19].replace('T',' ')} UTC &nbsp;|&nbsp; Data: {out.date} &nbsp;|&nbsp; Long-Only Swing Trading</p>

<div class="regime-badge">{out.regime_emoji} {out.regime}</div>

<div class="score-row">
  <div class="score-card"><div class="label">MM Score</div><div class="value" style="color:{'#00cc66' if out.mm_score>0 else '#ff6600'}">{out.mm_score:+.1f}</div></div>
  <div class="score-card"><div class="label">Chop Score</div><div class="value">{out.chop_score}/12</div></div>
  <div class="score-card"><div class="label">Risk Level</div><div class="value" style="font-size:1em">{out.risk_level}</div></div>
  <div class="score-card"><div class="label">Capital Deploy</div><div class="value">{out.risk_pct}%</div></div>
</div>

<div class="headline">{out.headline}</div>

<div class="section">
  <h2>🎯 Trading Action</h2>
  <span class="scan-badge">{'✅ SCAN TONIGHT' if out.scan_tonight else '❌ NO SCAN TONIGHT'}</span>
  <p><strong>{out.trading_action}</strong></p>
  <p style="margin-top:8px">{out.trading_action_detail}</p>
</div>

{'<div class="turnaround"><h2>🔄 Turnaround Signal</h2><p style="color:#ccc;margin-top:8px;line-height:1.6">' + out.turnaround_detail + '</p></div>' if out.turnaround_signal else ''}

<div class="section">
  <h2>📡 Key Signals</h2>
  <ul>{key_signals_html}</ul>
</div>

<div class="section">
  <h2>📋 Score Breakdown</h2>
  <table>{breakdown_html}</table>
</div>

<div class="section">
  <h2>🔍 Scan Guidance</h2>
  <p>{out.scan_guidance}</p>
</div>

<div class="section">
  <h2>👁️ Watch For (Next 3–5 Days)</h2>
  <ul>{watch_for_html}</ul>
</div>

<div class="section">
  <h2>✅ Action Items Tonight</h2>
  <ul>{action_items_html}</ul>
</div>

<div class="section">
  <h2>🧠 Coach Note</h2>
  <p>{out.coach_note}</p>
</div>

<div class="section">
  <h2>🎾 Mental Coaching</h2>
  <div class="mental-box">
    <div class="anchor">"{out.mental_anchor}"</div>
    <div class="reset">{out.mental_reset}</div>
  </div>
</div>

<div class="footer">
  SwingCoach — Built on 4,353 trading days (2009–2026) of Pradeep Bhonde's Market Monitor + QQQ data.<br>
  Inspired by Pradeep Bhonde · Kristjan Qullamaggie · Manas Arora · Paul Annacone · Jim Loehr<br>
  Long-only. No server. No cost. Just process.
</div>
</body>
</html>"""

    index_path = os.path.join(docs_dir, 'index.html')
    with open(index_path, 'w') as f:
        f.write(html)
    print(f"✅ index.html written: {index_path}")

    # ── Print summary ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"BRIEFING SUMMARY — {out.date}")
    print(f"{'='*60}")
    print(f"Regime:       {out.regime_emoji} {out.regime}")
    print(f"MM Score:     {out.mm_score:+.1f}")
    print(f"Chop Score:   {out.chop_score}/12 ({out.chop_regime})")
    print(f"Scan Tonight: {'YES ✅' if out.scan_tonight else 'NO ❌'}")
    print(f"Risk Level:   {out.risk_level} ({out.risk_pct}%)")
    print(f"Headline:     {out.headline}")
    print(f"{'='*60}")

if __name__ == "__main__":
    run()

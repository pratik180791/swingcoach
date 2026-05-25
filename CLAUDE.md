# SwingCoach — Developer Guide

## What This Is

SwingCoach is a serverless, $0-cost daily swing trading coaching system. It reads Pradeep Bhonde's public Market Monitor (MM) Google Sheet every weekday after market close, computes 13 breadth-based signals, classifies the market regime, and delivers a rules-based coaching briefing. No LLM required — all text is deterministic template output.

## Architecture

```
MM Google Sheet (public)
    ↓  daily at 4:30 PM ET
GitHub Actions (.github/workflows/daily_briefing.yml)
    ↓  runs Python engine
engine/coaching_engine.py  ←  core: data fetch, snapshot, scoring, templates
scripts/generate_briefing.py  ←  orchestrates engine → JSON + HTML
    ↓  writes to docs/
docs/briefing.json    ←  latest briefing (app/web reads this)
docs/history.json     ←  last 60 briefings
docs/index.html       ←  human-readable static web page
    ↓  served by GitHub Pages
Android app  ←  React Native / Expo (android_app/SwingCoach/)
Web browser  ←  reads docs/index.html or briefing.json directly
Telegram bot ←  (planned) GitHub Actions calls Telegram API after generating JSON
```

## Key Files

| File | Purpose |
|---|---|
| `engine/coaching_engine.py` | All logic: MM parsing, MMSnapshot, scoring, regime classification, template text |
| `scripts/generate_briefing.py` | Entry point: fetch → build snapshot → generate → write JSON + HTML |
| `docs/briefing.json` | Latest output (source of truth for all clients) |
| `docs/history.json` | Rolling 60-day history |
| `docs/index.html` | Static web briefing (auto-generated, not edited manually) |
| `android_app/SwingCoach/App.tsx` | React Native UI (5 tabs: Dashboard, Briefing, Signals, History, Learn) |
| `android_app/SwingCoach/src/services/briefingFetcher.ts` | URL config — update `YOUR_USERNAME` to your GitHub username |
| `.github/workflows/daily_briefing.yml` | Cron: weekdays 4:30 PM ET; also triggers Telegram send (planned) |

## Running Locally

```bash
cd home/ubuntu/swingcoach_repo
pip install requests pandas numpy yfinance
python scripts/generate_briefing.py
# Output written to docs/briefing.json and docs/index.html
```

## Deployment: GitHub Pages (Web)

1. Fork/clone the repo to your GitHub account
2. Settings → Pages → Source: `main` branch, `/docs` folder
3. Enable GitHub Actions
4. Run workflow manually once to seed the data
5. Live at `https://YOUR_USERNAME.github.io/swingcoach/`

## Deployment: Telegram Bot

Add to `.github/workflows/daily_briefing.yml` after the generate step:

```yaml
- name: Send Telegram briefing
  env:
    TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
    TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
  run: python scripts/send_telegram.py
```

Requires:
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in GitHub repo secrets
- `scripts/send_telegram.py` — reads `docs/briefing.json`, formats, sends via Bot API

## Deployment: Android App

```bash
cd android_app/SwingCoach
# 1. Update the GitHub Pages URL
# Edit src/services/briefingFetcher.ts — change YOUR_USERNAME to your GitHub username

# 2. Install and build
npm install
npm install -g eas-cli
eas login
eas build -p android --profile preview
# EAS builds in cloud (free tier: 30/month) and gives a download link
```

## Regime Reference

| Regime | MM Score | Capital Deploy |
|---|---|---|
| BREADTH_THRUST | thrust detected | 85% |
| STRONG_BULL | ≥ +8 | 75% |
| BULL | +3 to +8 | 65% |
| NEUTRAL | 0 to +3 | 35% |
| CHOPPY | chop ≥ 7/12 | 20% |
| BEAR | -4 to 0 | 10% |
| STRONG_BEAR | < -4 | 0% |
| EXTREME_OVERSOLD | T2108 < 20% | 5% |

## Development Priorities (Ordered)

1. ~~**Telegram bot**~~ ✅ Done — `scripts/send_telegram.py` + workflow step. Set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` secrets in GitHub repo.
2. **Android build** — update `GITHUB_USERNAME` in `briefingFetcher.ts` and run EAS build. App is complete, just needs the URL wired. See `SETUP.md` Step 5.
3. **Web polish** — the static `docs/index.html` is functional but auto-generated. A future upgrade: a PWA shell (React or vanilla JS) that reads `briefing.json` for a proper mobile-friendly web app.
4. **Push notifications** — once Android is deployed, add Expo push notification support so users get pinged at 5 PM ET.

## Constraints

- **$0 cost**: no paid APIs, no servers. GitHub Actions + GitHub Pages only.
- **No LLM in the pipeline**: all coaching text is rules-based templates in `coaching_engine.py`.
- **Long-only**: engine never suggests shorts. Bear regime → 100% cash advice.
- **Data dependency**: relies on Pradeep Bhonde's MM Google Sheet staying publicly accessible at the hardcoded URL.

## Architecture Decision Log

- Rules-based text (not LLM) was chosen to guarantee deterministic output and zero API cost.
- GitHub Pages chosen over Vercel/Railway/etc to keep the pipeline fully free.
- React Native (Expo) chosen for Android to allow EAS cloud builds without a Mac.

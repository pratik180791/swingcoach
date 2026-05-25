# 📊 SwingCoach

> A free, serverless AI swing trading coach built on 17 years of Pradeep Bhonde's Market Monitor data.
> Inspired by Pradeep Bhonde · Kristjan Qullamaggie · Manas Arora · Paul Annacone · Jim Loehr.
> **Long-only. No server. No cost. Just process.**

---

## How It Works

```
Pradeep Bhonde's MM Google Sheet (public)
        ↓  (fetched daily at 4:30 PM ET)
GitHub Actions (free) runs Python coaching engine
        ↓  (generates briefing.json + index.html)
GitHub Pages (free) hosts the output
        ↓  (Android app reads the JSON)
Your phone shows the daily briefing
```

**Total cost: $0.** No cloud server. No subscription. Just your phone and GitHub.

---

## Setup Guide (One-Time, ~10 minutes)

### Step 1: Fork or Clone This Repository

```bash
git clone https://github.com/YOUR_USERNAME/swingcoach.git
cd swingcoach
```

Or click **Fork** on GitHub to create your own copy.

### Step 2: Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** → **Pages** (left sidebar)
3. Under **Source**, select **Deploy from a branch**
4. Branch: `main` | Folder: `/docs`
5. Click **Save**

Your briefing will be live at:
```
https://YOUR_USERNAME.github.io/swingcoach/
```

And the JSON endpoint for the app:
```
https://YOUR_USERNAME.github.io/swingcoach/briefing.json
```

### Step 3: Enable GitHub Actions

1. Go to **Actions** tab in your repository
2. Click **"I understand my workflows, go ahead and enable them"**
3. The workflow runs automatically every weekday at **4:30 PM ET**

### Step 4: Run Your First Briefing Manually

1. Go to **Actions** → **SwingCoach Daily Briefing**
2. Click **Run workflow** → **Run workflow**
3. Wait ~60 seconds
4. Visit your GitHub Pages URL to see the briefing

### Step 5: Install the Android App

See the `android_app/` folder for the React Native (Expo) app.

**Quick setup:**
```bash
cd android_app/SwingCoach
npm install -g eas-cli
eas login          # create free Expo account at expo.dev
eas build -p android --profile preview
```

EAS will build your APK in the cloud (free tier: 30 builds/month) and give you a download link.

**Before building**, update the API URL in the app:
```
android_app/SwingCoach/src/services/briefingFetcher.ts
```
Change `YOUR_USERNAME` to your GitHub username.

---

## Repository Structure

```
swingcoach/
├── .github/
│   └── workflows/
│       └── daily_briefing.yml    ← GitHub Actions: runs daily at 4:30 PM ET
├── engine/
│   └── coaching_engine.py        ← v3 coaching engine (Python)
├── scripts/
│   └── generate_briefing.py      ← Generates JSON + HTML output
├── docs/                         ← GitHub Pages serves this folder
│   ├── briefing.json             ← Latest briefing (app reads this)
│   ├── history.json              ← Last 60 briefings (history tab)
│   └── index.html                ← Human-readable web version
├── android_app/
│   └── SwingCoach/               ← React Native Expo app
├── requirements.txt
└── README.md
```

---

## The Coaching Engine

Built on **4,353 trading days (2009–2026)** of Pradeep Bhonde's MM data merged with QQQ OHLC.

### MM Score Components (13 total)

| Component | What It Measures | Weight |
|---|---|---|
| Daily Breadth | Up4Pct / Down4Pct ratio | ±3.0 |
| 5-Day Ratio | Primary trend signal | ±2.0 |
| 5d Ratio Trend | 3-day direction of change | ±0.5 |
| Quarter Breadth | Rally participation quality | ±2.5 |
| Qtr Breadth Trend | Expanding vs contracting | ±1.5 |
| Down Qtr Breadth | Damage accumulating under surface | ±1.5 |
| T2108 | Market temperature + trend | ±1.5 |
| 34/13 Day Trend | Intermediate cycle | ±1.5 |
| Month Damage | Down25PctMonth as leading signal | ±1.0 |
| Euphoria | Up50PctMonth exhaustion | ±2.0 |
| QQQ vs 20MA | Index position filter | ±1.5 |
| Bull/Bear Streak | Momentum confirmation | ±1.5 |
| Breadth Thrust | Launch pad signal (72% win rate) | +3.0 |

### Regimes

| Regime | MM Score | Capital Deployment | Scan? |
|---|---|---|---|
| BREADTH_THRUST | Thrust detected | 85% | YES — aggressive |
| STRONG_BULL | ≥ +8 | 75% | YES — full scan |
| BULL | +3 to +8 | 65% | YES |
| NEUTRAL | 0 to +3 | 35% | Selective only |
| CHOPPY | Chop ≥ 7/12 | 20% | Cautious |
| BEAR | -4 to 0 | 10% | NO |
| STRONG_BEAR | < -4 | 0% | NO — 100% cash |
| EXTREME_OVERSOLD | T2108 < 20% | 5% | NO — wait for signal |

### Choppiness Index (0–12)

Five components validated against known choppy periods (2015–16, 2018 Q4, 2022, 2023 summer):
1. Two-way action (both Up4 AND Down4 elevated)
2. 5-day ratio in 0.85–1.15 zone
3. Quarter breadth flat (3d change < ±30)
4. T2108 stuck in 42–65% band
5. Near-zero net breadth (|Up4 − Down4| < 50)

---

## Key Statistical Findings

| Signal | N (2009–2026) | Win Rate | Avg 5d Return |
|---|---|---|---|
| Breadth Thrust | 110 | 60% | +0.58% |
| Extreme Oversold | 73 | 69.9% | +1.77% |
| Strong Bull Broad | 628 | 58.8% | +0.31% |
| Bull Continuation | 1,123 | 58.4% | +0.20% |
| Bear Confirmed | 154 | 58.4% | +0.46% |

> **No look-ahead bias.** All forward returns are computed strictly from close of T to close of T+N.
> MM data published after market close is only used to predict T+1 forward.

---

## Philosophy

This system does not predict the market. It tells you **when to take risk** and **when to protect capital**.

> *"The most important skill is not making money — it's not losing money. If you can protect your capital during bad markets, you'll be there for the good ones."* — Kristjan Qullamaggie

> *"When the 5-day ratio is above 1.3 and quarter breadth is expanding, your job is to be in the best setups you can find."* — Pradeep Bhonde

> *"Process over outcome."* — Manas Arora

---

## License

MIT — use freely, improve freely, share freely.

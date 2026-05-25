# SwingCoach — Setup Guide

This guide covers everything needed to get SwingCoach running for a new owner.
Total setup time: ~15 minutes. Total ongoing cost: **$0**.

---

## What You're Setting Up

```
GitHub Actions (free)
    runs daily at 4:30 PM ET
    → generates briefing.json + index.html
    → commits to your repo
    → sends Telegram message (optional)

GitHub Pages (free)
    serves docs/ folder as a website
    → https://YOUR_USERNAME.github.io/swingcoach/

Android App (optional, one-time build via Expo EAS free tier)
    reads briefing.json from your GitHub Pages URL
```

---

## Step 1 — Fork the Repository

1. Go to https://github.com/ORIGINAL_OWNER/swingcoach
2. Click **Fork** (top right)
3. Name it `swingcoach` — the GitHub Pages URL will be `https://YOUR_USERNAME.github.io/swingcoach/`

---

## Step 2 — Enable GitHub Pages

1. Go to your forked repo → **Settings** → **Pages** (left sidebar)
2. Source: **Deploy from a branch**
3. Branch: `main` | Folder: `/docs`
4. Click **Save**

Your web briefing will be live at:
```
https://YOUR_USERNAME.github.io/swingcoach/
```

---

## Step 3 — Enable GitHub Actions

1. Go to **Actions** tab in your repo
2. Click **"I understand my workflows, go ahead and enable them"**
3. The workflow now runs automatically every weekday at 4:30 PM ET

**Run your first briefing manually:**
1. Actions → **SwingCoach Daily Briefing** → **Run workflow** → **Run workflow**
2. Wait ~60 seconds
3. Visit your GitHub Pages URL — the briefing should appear

---

## Step 4 — Telegram Bot (Optional but Recommended)

### 4a. Create your Telegram bot

1. Open Telegram → search for **@BotFather** → start a chat
2. Send: `/newbot`
3. Choose a name (e.g. "My SwingCoach") and a username (e.g. `myswingcoach_bot`)
4. BotFather gives you a **token** — looks like `7123456789:AAFabc...` — copy it

### 4b. Get your chat ID

**For a personal chat (bot sends to you directly):**
1. Search for your new bot in Telegram and start a chat with it (send `/start`)
2. Visit: `https://api.telegram.org/botYOUR_TOKEN/getUpdates`
3. Look for `"chat":{"id":XXXXXXXXX}` — that number is your chat ID

**For a channel (bot broadcasts to a channel):**
1. Create a Telegram channel
2. Add your bot as an **Administrator** of the channel
3. Your chat ID is `@your_channel_username` (for public channels) or a negative number like `-1001234567890` (for private channels — get it from getUpdates after posting a test message)

### 4c. Add secrets to your GitHub repo

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** for each:

| Secret name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | The token from BotFather |
| `TELEGRAM_CHAT_ID` | Your personal chat ID or `@channelname` |

Done. The next time GitHub Actions runs (or when you trigger it manually), it will send the briefing to Telegram automatically.

**What the Telegram message looks like:**
```
📊 SwingCoach — 2026-05-12

🟩 BULL  |  MM: +5.2  |  Chop: 3/12

The broad market is healthy. Focus on the best setups.

✅ SCAN TONIGHT  |  Capital: 65%  |  Risk: MODERATE

  • Daily breadth: 612 up / 221 dn (ratio 2.77) — Strong
  • 5-day ratio: 1.48 — Bullish | 3d trend: improving
  • Quarter breadth: 1890 stocks up 25%+ — Broad participation

Full briefing → https://YOUR_USERNAME.github.io/swingcoach/
```

---

## Step 5 — Android App (Optional)

The Android app shows all five tabs (Dashboard, Briefing, Signals, History, Learn) and auto-refreshes every 4 hours.

### 5a. Update the GitHub Pages URL in the app

Open this file and change `YOUR_USERNAME` to your GitHub username:
```
android_app/SwingCoach/src/services/briefingFetcher.ts
```

Line 13:
```typescript
const GITHUB_USERNAME = 'YOUR_USERNAME';  // ← change this
```

That's the only code change needed.

### 5b. Build the APK

```bash
cd android_app/SwingCoach

# Install Expo EAS CLI (one-time)
npm install -g eas-cli

# Log in (free account at expo.dev)
eas login

# Build the APK in Expo's cloud (free tier: 30 builds/month)
eas build -p android --profile preview
```

EAS will give you a link to download the `.apk` file when it's done (~5-10 minutes).

### 5c. Install on your phone

1. Enable **Install from unknown sources** in Android settings
2. Download and open the APK
3. The app will show today's briefing on launch

---

## Ongoing Maintenance

**You don't need to do anything.** GitHub Actions runs every weekday automatically.

The only things that could break:
- **MM Google Sheet URL changes**: If Pradeep Bhonde restructures his sheet, update `MM_CSV_URL` in `engine/coaching_engine.py`. Check the Actions tab — a failed run sends an email to your GitHub account.
- **Telegram bot blocked**: If the bot is blocked, re-create it via BotFather and update the `TELEGRAM_BOT_TOKEN` secret.

**To check if today's briefing ran:** Go to Actions → SwingCoach Daily Briefing → latest run. Green checkmark = success.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| GitHub Pages shows old content | Wait 1-2 min for Pages to rebuild after Actions pushes |
| Telegram not sending | Check Actions logs for the "Send Telegram briefing" step. Verify secrets are set correctly. |
| Actions workflow failing | Check Actions tab for the error. Most likely cause: MM Google Sheet URL changed. |
| Android app shows "Could not fetch" | Confirm your GitHub Pages URL is live and `GITHUB_USERNAME` in `briefingFetcher.ts` matches your username |

---

## Repo Structure (Quick Reference)

```
swingcoach/
├── .github/workflows/daily_briefing.yml  ← cron job + Telegram send
├── engine/coaching_engine.py             ← all scoring logic + templates
├── scripts/
│   ├── generate_briefing.py              ← orchestrates engine → JSON + HTML
│   └── send_telegram.py                  ← formats + sends Telegram message
├── docs/                                 ← GitHub Pages serves this
│   ├── briefing.json                     ← latest briefing (source of truth)
│   ├── history.json                      ← last 60 briefings
│   └── index.html                        ← auto-generated web page
├── android_app/SwingCoach/               ← React Native / Expo app
│   └── src/services/briefingFetcher.ts   ← ← UPDATE YOUR_USERNAME HERE
├── SETUP.md                              ← this file
├── CLAUDE.md                             ← developer guide
└── README.md                             ← project overview
```

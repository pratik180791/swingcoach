# SwingCoach Project Handover Document

## 1. Project Mission & Vision
**SwingCoach** is a personalized, AI-driven swing trading coaching system. Its mission is to bridge the gap between complex market breadth data and actionable trading psychology. The user is a long-only swing trader who lacks the daily focus and breadth interpretation skills of market wizards. SwingCoach solves this by reading raw market breadth data daily, analyzing it through the lens of elite traders (Pradeep Bhonde, Kristjan Qullamaggie, Manas Arora), and delivering a concise, psychologically grounded morning briefing.

The system is completely serverless, costing $0 to operate. It runs via a GitHub Actions pipeline that generates a static JSON briefing, which is then consumed by a lightweight, self-contained React Native (Expo) Android application.

## 2. Core Architecture & Workflow
The system is built on a "headless engine + thin client" architecture:

1. **Data Source**: Pradeep Bhonde's public "MM" (Market Monitor) Google Sheet, which tracks daily market breadth metrics (2007–Present).
2. **The Brain (Python Engine)**: A Python script (`generate_briefing.py`) running on GitHub Actions every weekday at 4:30 PM ET. It fetches the live MM data, computes rolling features, determines the market regime, and generates the coaching text **using a 100% rules-based template system (no LLM required)**.
3. **The Output**: The engine writes the output to `docs/briefing.json` and hosts it via GitHub Pages.
4. **The Client**: A React Native Android app that fetches the JSON from GitHub Pages and renders the Dashboard, Briefing, History, and Mental Coaching tabs.

## 3. The Breadth Framework & Statistical Findings
The coaching engine's logic is derived from a deep analysis of 17 years (4,353 trading days) of MM data merged with QQQ historical prices. The analysis revealed that breadth indicators are highly non-linear. The most predictive signals come from the *trajectory* of breadth over 3–5 days, not a single day's reading.

### Key Metrics & Definitions
- **Daily Ratio**: `Up4% / Down4%`. Measures daily conviction.
- **5-Day Ratio**: The core momentum gauge. >1.3 is bullish, <0.85 is bearish.
- **Quarter Breadth**: `Up25% in a quarter`. The foundation of the market trend.
- **Month Breadth**: `Up25% in a month`. The current wave of momentum.
- **T2108**: % of stocks above their 40-day moving average. A primary overbought/oversold oscillator.

### The Trend Freshness Layer (v4 Upgrade)
To help the user identify Qullamaggie-style momentum setups, the engine calculates five advanced "trend freshness" metrics:
1. **Freshness Ratio** (`Month Breadth / Quarter Breadth`): High = new stocks joining the rally (early bull). Low = same leaders carrying the index (late bull).
2. **Euphoria Ratio** (`Up50% Month / Month Breadth`): High = leaders are parabolic and extended.
3. **Acceleration Ratio** (`34-Day Breadth / Quarter Breadth`): >1.2 indicates the intermediate trend is accelerating.
4. **Monthly Momentum** (`Month Up / Month Down`): The primary gauge for scan quality. >3.0x is an excellent environment.
5. **Damage Ratio** (`Down Quarter / Up Quarter`): Measures market bifurcation. High damage while the index is up indicates dangerous under-the-surface deterioration.

### Regime Classification
The engine classifies the market into 5 primary regimes (Strong Bull, Bull, Neutral, Bear, Strong Bear) and overlays a **Choppiness Index** (0-12 scale). If the Chop Score is ≥7, the regime is overridden to CHOPPY, and the user is advised to stop scanning for new longs.

## 4. Coaching Philosophy, Voice & Text Generation Architecture
A critical architectural decision of SwingCoach is that **it does NOT use an LLM API to generate the daily briefing text.** 

To maintain the strict requirement of being 100% free and serverless without requiring API keys, the text generation is handled by a **deterministic, rules-based template engine** inside `coaching_engine.py`.

### How the Text is Generated (No LLM Required)
1. The engine calculates the numerical scores (Regime, Chop Score, Freshness, etc.).
2. These scores map to specific, pre-written text blocks and string templates.
3. The exact quotes from Kristjan Qullamaggie, Pradeep Bhonde, and Brad Gilbert were extracted by Manus AI during the research phase and hardcoded into these templates based on the specific market regime they apply to.
4. The engine injects the live numerical data (e.g., `f"{snap.up25month} stocks joined the move"`) into the pre-written psychological frameworks.

This guarantees that the coaching voice remains exactly as intended, never hallucinates, and costs absolutely nothing to run every day.

### The Coaching Voice Components
- **Market Interpretation**: Uses Pradeep Bhonde's structural breadth analysis.
- **Trading Action**: Uses Kristjan Qullamaggie's exact quotes regarding momentum, sitting out in chop, and letting leaders run.
- **Mental Coaching Layer**: Integrates sports psychology frameworks from Paul Annacone (Federer's coach), Novak Djokovic's visualization techniques, and Jim Loehr's Ideal Performance State. Every briefing includes a "Pre-Session Reset" breathing exercise and a "Mental Anchor" quote.
- **Strictly Long-Only**: The engine never suggests shorting. In bearish regimes, the advice is 100% cash.

## 5. Limitations & Known Biases
1. **Survivorship Bias in MM Data**: Pradeep Bhonde's Worden universe only tracks currently active stocks. Delisted or bankrupt stocks from 2009–2015 are not in the historical data, which slightly skews historical bear market metrics.
2. **QQQ Proxy**: The backtest validation used QQQ as the benchmark. The engine guides overall market exposure, not individual stock selection.
3. **End-of-Day Reliance**: The system runs entirely on closing data. It does not provide intraday alerts or real-time breadth thrust notifications.
4. **Google Sheet Dependency**: The data pipeline relies on the public URL of Pradeep's Google Sheet. If the sheet structure changes (e.g., columns are added/removed), the Python parser (`coaching_engine.py`) will need to be updated.

## 6. Scope for Improvement & Next Steps
For the next LLM agent or developer taking over this project, here is the roadmap:

1. **LLM Synthesis Layer (Optional Upgrade)**: While the current rules-based text generation is robust and free, an optional upgrade would be to pass the raw `briefing.json` data through an LLM API (like OpenAI) *only if* the user provides an API key. This would allow for more fluid, conversational daily briefings rather than structured templates.
2. **Individual Stock Scanning Integration**: The engine currently tells the user *whether* to scan and *what parameters* to use. The next evolution is to connect to a stock screener API (e.g., Finviz or Polygon) to actually run the Qullamaggie momentum scan and deliver the top 5 ticker candidates directly in the app.
2. **Sector Rotation Analysis**: Pradeep's MM page often includes sector breadth. Scraping and analyzing sector-level data would allow the coach to say, "The market is choppy, but money is rotating into Energy."
3. **User Portfolio Integration**: Allow the user to input their current open positions into the app. The coach could then give specific advice: "The damage ratio is spiking. Tighten your stop on AAPL to the 10-day MA."
4. **Push Notifications**: Upgrade the React Native app to support local push notifications so the user gets a ping at 5:00 PM ET when the new briefing is ready.

## 7. Synthesized AI Prompt for Project Resumption
If starting a new chat session to continue development, use the following prompt to instantly align the new agent:

> **System Prompt for Resumption:**
> "You are the lead developer and trading analyst for **SwingCoach**, a serverless, AI-driven swing trading coaching system. The system reads Pradeep Bhonde's Market Monitor (MM) Google Sheet daily via a GitHub Actions Python script, computes non-linear breadth metrics (including a 5-component Choppiness Index and a 5-metric Trend Freshness layer), and outputs a JSON briefing. This JSON is consumed by a React Native Android app. The coaching voice blends Pradeep's breadth analysis, Kristjan Qullamaggie's momentum philosophy and exact quotes, and elite sports psychology (Federer/Djokovic mental frameworks). The user trades strictly long-only momentum setups. Note that the text generation is currently 100% rules-based and deterministic (no LLM API calls) to keep costs at $0. Your goal is to maintain the system's architectural simplicity while enhancing its predictive power and psychological impact. Read `SWINGCOACH_HANDOVER.md` and `engine/coaching_engine.py` to understand the current state, then ask the user what feature we are building next."

---
*Generated by Manus AI — May 2026*

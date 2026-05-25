/**
 * SwingCoach Android App
 * ━━━━━━━━━━━━━━━━━━━━━━
 * Reads daily briefing from GitHub Pages (free hosting).
 * No server. No subscription. Long-only swing trading coach.
 *
 * Tabs:
 *   📊 Dashboard  — Regime, score, scan signal, key metrics
 *   📋 Briefing   — Full coaching text + mental coaching
 *   📡 Signals    — All key signals + score breakdown
 *   📈 History    — Last 30 days of breadth readings
 *   🧠 Learn      — MM framework reference
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, RefreshControl,
  StyleSheet, StatusBar, Linking, ActivityIndicator,
  Dimensions, Platform
} from 'react-native';
import {
  fetchBriefing, fetchHistory, getRegimeColor, getRegimeDescription,
  isDataStale, Briefing, HistoryEntry, WEB_URL
} from './src/services/briefingFetcher';

const { width } = Dimensions.get('window');

// ─── THEME ────────────────────────────────────────────────────────────────────
const T = {
  bg:       '#0a0a0f',
  card:     '#1a1a2e',
  card2:    '#12121f',
  border:   '#2a2a3e',
  text:     '#e0e0e0',
  textDim:  '#888888',
  textBold: '#ffffff',
  green:    '#00cc66',
  red:      '#ff4444',
  orange:   '#ff8800',
  yellow:   '#ffaa00',
  purple:   '#ff00ff',
};

// ─── TABS ─────────────────────────────────────────────────────────────────────
type Tab = 'dashboard' | 'briefing' | 'signals' | 'history' | 'learn';

// ─── MAIN APP ─────────────────────────────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState<Tab>('dashboard');
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [fromCache, setFromCache] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (force = false) => {
    if (!force) setLoading(true);
    const [bResult, hResult] = await Promise.all([
      fetchBriefing(force),
      fetchHistory(force),
    ]);
    setBriefing(bResult.briefing);
    setHistory(hResult.history);
    setFromCache(bResult.fromCache);
    setError(bResult.error || hResult.error || null);
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const onRefresh = () => { setRefreshing(true); load(true); };

  if (loading) return <LoadingScreen />;

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor={T.bg} />
      {error && <ErrorBanner message={error} />}
      {fromCache && briefing && isDataStale(briefing.generated_at) && (
        <StaleBanner />
      )}

      <ScrollView
        style={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={T.green} />}
        showsVerticalScrollIndicator={false}
      >
        {tab === 'dashboard' && <DashboardTab briefing={briefing} />}
        {tab === 'briefing'  && <BriefingTab  briefing={briefing} />}
        {tab === 'signals'   && <SignalsTab   briefing={briefing} />}
        {tab === 'history'   && <HistoryTab   history={history}   />}
        {tab === 'learn'     && <LearnTab />}
        <View style={{ height: 80 }} />
      </ScrollView>

      <BottomNav tab={tab} setTab={setTab} />
    </View>
  );
}

// ─── DASHBOARD TAB ────────────────────────────────────────────────────────────
function DashboardTab({ briefing }: { briefing: Briefing | null }) {
  if (!briefing) return <EmptyState />;
  const rc = getRegimeColor(briefing.regime);

  return (
    <View style={styles.tab}>
      <Text style={styles.pageTitle}>📊 Daily Briefing</Text>
      <Text style={styles.dateText}>{briefing.date}</Text>

      {/* Regime Badge */}
      <View style={[styles.regimeBadge, { backgroundColor: rc }]}>
        <Text style={styles.regimeText}>{briefing.regime_emoji} {briefing.regime}</Text>
        <Text style={styles.regimeDesc}>{getRegimeDescription(briefing.regime)}</Text>
      </View>

      {/* Score Row */}
      <View style={styles.scoreRow}>
        <ScoreCard label="MM Score" value={`${briefing.mm_score > 0 ? '+' : ''}${briefing.mm_score}`}
          color={briefing.mm_score > 0 ? T.green : T.red} />
        <ScoreCard label="Chop" value={`${briefing.chop_score}/12`}
          color={briefing.chop_score >= 7 ? T.orange : T.green} />
        <ScoreCard label="Capital" value={`${briefing.risk_pct}%`}
          color={briefing.risk_pct >= 65 ? T.green : briefing.risk_pct >= 35 ? T.yellow : T.red} />
      </View>

      {/* Scan Tonight */}
      <View style={[styles.scanCard, { borderColor: briefing.scan_tonight ? T.green : T.red }]}>
        <Text style={[styles.scanLabel, { color: briefing.scan_tonight ? T.green : T.red }]}>
          {briefing.scan_tonight ? '✅ SCAN TONIGHT' : '❌ NO SCAN TONIGHT'}
        </Text>
        <Text style={styles.scanAction}>{briefing.trading_action}</Text>
        <Text style={styles.scanDetail}>{briefing.trading_action_detail}</Text>
      </View>

      {/* Turnaround Signal */}
      {briefing.turnaround_signal && (
        <View style={styles.turnaroundCard}>
          <Text style={styles.turnaroundTitle}>🔄 TURNAROUND SIGNAL</Text>
          <Text style={styles.turnaroundText}>{briefing.turnaround_detail}</Text>
        </View>
      )}

      {/* Headline */}
      <View style={[styles.card, { borderLeftWidth: 3, borderLeftColor: rc }]}>
        <Text style={styles.headline}>{briefing.headline}</Text>
      </View>

      {/* Key MM Values */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📡 MM Snapshot</Text>
        <MMRow label="Up4Pct / Down4Pct" value={`${briefing.mm_raw.up4} / ${briefing.mm_raw.dn4}`} />
        <MMRow label="5-Day Ratio" value={briefing.mm_raw.ratio5.toFixed(2)}
          color={briefing.mm_raw.ratio5 > 1.3 ? T.green : briefing.mm_raw.ratio5 > 0.9 ? T.yellow : T.red} />
        <MMRow label="Quarter Breadth" value={`${briefing.mm_raw.up25qtr} up / ${briefing.mm_raw.dn25qtr} dn`} />
        <MMRow label="T2108" value={`${briefing.mm_raw.t2108.toFixed(1)}%`}
          color={briefing.mm_raw.t2108 < 20 ? T.orange : briefing.mm_raw.t2108 > 80 ? T.red : T.green} />
        <MMRow label="34/13 Ratio" value={briefing.mm_raw.ratio34_13.toFixed(2)} />
        <MMRow label="Bull Streak" value={`${briefing.mm_raw.bull_streak} days`}
          color={briefing.mm_raw.bull_streak >= 3 ? T.green : T.textDim} />
        {briefing.mm_raw.breadth_thrust && (
          <MMRow label="🚀 BREADTH THRUST" value="DETECTED" color={T.purple} />
        )}
      </View>

      {/* Watch For */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>👁️ Watch For</Text>
        {briefing.watch_for.map((w, i) => (
          <Text key={i} style={styles.bulletItem}>→ {w}</Text>
        ))}
      </View>

      {/* Action Items */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>✅ Tonight's Actions</Text>
        {briefing.action_items.map((a, i) => (
          <Text key={i} style={styles.bulletItem}>• {a}</Text>
        ))}
      </View>
    </View>
  );
}

// ─── BRIEFING TAB ─────────────────────────────────────────────────────────────
function BriefingTab({ briefing }: { briefing: Briefing | null }) {
  if (!briefing) return <EmptyState />;

  return (
    <View style={styles.tab}>
      <Text style={styles.pageTitle}>📋 Full Briefing</Text>

      {/* Scan Guidance */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🔍 Scan Guidance</Text>
        <Text style={styles.preText}>{briefing.scan_guidance}</Text>
      </View>

      {/* Coach Note */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🧠 Coach Note</Text>
        <Text style={styles.bodyText}>{briefing.coach_note}</Text>
      </View>

      {/* Mental Coaching */}
      <View style={[styles.card, { borderColor: '#333' }]}>
        <Text style={styles.cardTitle}>🎾 Mental Coaching</Text>
        <View style={styles.anchorBox}>
          <Text style={styles.anchorText}>"{briefing.mental_anchor}"</Text>
        </View>
        <Text style={[styles.cardTitle, { marginTop: 14, fontSize: 11 }]}>PRE-SESSION RESET</Text>
        <Text style={styles.preText}>{briefing.mental_reset}</Text>
      </View>

      {/* Trading Action Detail */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🎯 Trading Action Detail</Text>
        <Text style={styles.bodyText}>{briefing.trading_action_detail}</Text>
      </View>

      {/* Open in Browser */}
      <TouchableOpacity style={styles.webButton} onPress={() => Linking.openURL(WEB_URL)}>
        <Text style={styles.webButtonText}>🌐 Open Full Briefing in Browser</Text>
      </TouchableOpacity>
    </View>
  );
}

// ─── SIGNALS TAB ──────────────────────────────────────────────────────────────
function SignalsTab({ briefing }: { briefing: Briefing | null }) {
  if (!briefing) return <EmptyState />;

  return (
    <View style={styles.tab}>
      <Text style={styles.pageTitle}>📡 Signals & Breakdown</Text>

      {/* Key Signals */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>KEY SIGNALS</Text>
        {briefing.key_signals.map((s, i) => (
          <Text key={i} style={[styles.bulletItem, { marginBottom: 8 }]}>{s}</Text>
        ))}
      </View>

      {/* Score Breakdown */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>SCORE BREAKDOWN</Text>
        <View style={styles.breakdownHeader}>
          <Text style={[styles.breakdownCell, { flex: 2, color: T.textDim }]}>Component</Text>
          <Text style={[styles.breakdownCell, { flex: 0.6, textAlign: 'right', color: T.textDim }]}>Score</Text>
          <Text style={[styles.breakdownCell, { flex: 3, color: T.textDim }]}>Reading</Text>
        </View>
        {briefing.breakdown.map((b, i) => (
          <View key={i} style={styles.breakdownRow}>
            <Text style={[styles.breakdownCell, { flex: 2 }]}>{b.component}</Text>
            <Text style={[styles.breakdownCell, { flex: 0.6, textAlign: 'right',
              color: b.score > 0 ? T.green : b.score < 0 ? T.red : T.textDim }]}>
              {b.score > 0 ? '+' : ''}{b.score.toFixed(1)}
            </Text>
            <Text style={[styles.breakdownCell, { flex: 3, color: T.textDim, fontSize: 11 }]}>{b.label}</Text>
          </View>
        ))}
        <View style={[styles.breakdownRow, { borderTopWidth: 1, borderTopColor: T.border, marginTop: 6, paddingTop: 6 }]}>
          <Text style={[styles.breakdownCell, { flex: 2, color: T.textBold, fontWeight: 'bold' }]}>TOTAL</Text>
          <Text style={[styles.breakdownCell, { flex: 0.6, textAlign: 'right', fontWeight: 'bold',
            color: briefing.mm_score > 0 ? T.green : T.red }]}>
            {briefing.mm_score > 0 ? '+' : ''}{briefing.mm_score}
          </Text>
          <Text style={[styles.breakdownCell, { flex: 3, color: T.textDim, fontSize: 11 }]}>{briefing.regime}</Text>
        </View>
      </View>

      {/* Chop Analysis */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>〰️ CHOPPINESS INDEX</Text>
        <View style={styles.chopBar}>
          <View style={[styles.chopFill, {
            width: `${(briefing.chop_score / 12) * 100}%`,
            backgroundColor: briefing.chop_score >= 9 ? T.red : briefing.chop_score >= 7 ? T.orange : T.green
          }]} />
        </View>
        <Text style={styles.chopLabel}>{briefing.chop_score}/12 — {briefing.chop_regime}</Text>
        <Text style={styles.bodyText}>
          {briefing.chop_score >= 9
            ? 'EXTREME CHOP: This is a whipsaw environment. Avoid new longs.'
            : briefing.chop_score >= 7
            ? 'CHOPPY: Be very selective. Reduce size significantly.'
            : briefing.chop_score >= 4
            ? 'MIXED: Some chop present. Focus on the cleanest setups.'
            : 'TRENDING: Low choppiness. Good environment for swing longs.'}
        </Text>
      </View>
    </View>
  );
}

// ─── HISTORY TAB ──────────────────────────────────────────────────────────────
function HistoryTab({ history }: { history: HistoryEntry[] }) {
  if (!history.length) return <EmptyState message="No history yet. Check back after the first briefing is generated." />;

  return (
    <View style={styles.tab}>
      <Text style={styles.pageTitle}>📈 Breadth History</Text>
      <Text style={styles.dateText}>Last {history.length} trading days</Text>

      {/* Mini chart of ratio5 */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>5-DAY RATIO TREND</Text>
        <View style={styles.miniChart}>
          {history.slice(0, 20).reverse().map((h, i) => {
            const height = Math.min(Math.max((h.ratio5 - 0.5) / 1.5 * 60, 4), 60);
            const color = h.ratio5 > 1.3 ? T.green : h.ratio5 > 0.9 ? T.yellow : T.red;
            return (
              <View key={i} style={styles.barWrapper}>
                <View style={[styles.bar, { height, backgroundColor: color }]} />
              </View>
            );
          })}
        </View>
        <View style={styles.chartLegend}>
          <Text style={[styles.legendDot, { color: T.green }]}>■ Bull (>1.3)</Text>
          <Text style={[styles.legendDot, { color: T.yellow }]}>■ Chop (0.9–1.3)</Text>
          <Text style={[styles.legendDot, { color: T.red }]}>■ Bear (<0.9)</Text>
        </View>
      </View>

      {/* History rows */}
      {history.map((h, i) => (
        <View key={i} style={[styles.historyRow, { borderLeftColor: getRegimeColor(h.regime) }]}>
          <View style={styles.historyLeft}>
            <Text style={styles.historyDate}>{h.date}</Text>
            <Text style={[styles.historyRegime, { color: getRegimeColor(h.regime) }]}>{h.regime}</Text>
          </View>
          <View style={styles.historyRight}>
            <Text style={styles.historyVal}>R5: <Text style={{ color: h.ratio5 > 1.3 ? T.green : h.ratio5 > 0.9 ? T.yellow : T.red }}>{h.ratio5.toFixed(2)}</Text></Text>
            <Text style={styles.historyVal}>T2108: {h.t2108.toFixed(0)}%</Text>
            <Text style={styles.historyVal}>QtrB: {h.up25qtr}</Text>
            <Text style={[styles.historyVal, { color: h.scan_tonight ? T.green : T.red }]}>
              {h.scan_tonight ? '✅ Scan' : '❌ No scan'}
            </Text>
          </View>
        </View>
      ))}
    </View>
  );
}

// ─── LEARN TAB ────────────────────────────────────────────────────────────────
function LearnTab() {
  return (
    <View style={styles.tab}>
      <Text style={styles.pageTitle}>🧠 The MM Framework</Text>
      <Text style={styles.dateText}>Pradeep Bhonde's Market Monitor — Explained</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>THE CORE IDEA</Text>
        <Text style={styles.bodyText}>
          The MM tells you not WHAT the market will do, but WHETHER to take risk.
          {'\n\n'}
          "When the 5-day ratio is above 1.3 and quarter breadth is expanding, your job is to be in the best setups you can find." — Pradeep Bhonde
          {'\n\n'}
          "In choppy markets, the best trade is often no trade." — Kristjan Qullamaggie
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>KEY INDICATORS</Text>
        {[
          ['Up4Pct / Down4Pct', 'Daily breadth pulse. How many stocks moved 4%+ today in each direction. The ratio tells you who won the day.'],
          ['5-Day Ratio', 'PRIMARY SIGNAL. Ratio of up4 days to down4 days over 5 days. >1.3 = bull, 0.9–1.1 = chop, <0.85 = bear.'],
          ['Quarter Breadth', 'Stocks up 25%+ this quarter. >1000 = broad healthy rally. <400 = narrow, dangerous.'],
          ['Down Qtr Breadth', 'LEADING SIGNAL. Stocks down 25%+ this quarter. Rising = damage accumulating under the surface.'],
          ['T2108', 'Market temperature. % of stocks above 40-week MA. <20% = extreme oversold. >80% = overbought.'],
          ['34/13 Day Ratio', 'Intermediate trend. Stocks up 13%+ in 34 days vs down. >1.5 = strong intermediate uptrend.'],
          ['Up50PctMonth', 'Euphoria indicator. >100 stocks up 50%+ in a month = late stage. Tighten stops.'],
          ['Choppiness Index', 'MM-derived. 5 components. Score ≥7 = whipsaw environment. Avoid new longs.'],
        ].map(([name, desc], i) => (
          <View key={i} style={styles.learnRow}>
            <Text style={styles.learnName}>{name}</Text>
            <Text style={styles.learnDesc}>{desc}</Text>
          </View>
        ))}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>REGIME GUIDE</Text>
        {[
          ['🚀 BREADTH_THRUST', '#ff00ff', '72% win rate. +2.1% avg 5d. Maximum aggression.'],
          ['🚀 STRONG_BULL', '#00ff88', 'Broad participation. Full scan. 75% capital.'],
          ['📈 BULL', '#00cc66', 'Good conditions. Scan tonight. 65% capital.'],
          ['⚖️ NEUTRAL', '#ffaa00', 'Mixed signals. Selective only. 35% capital.'],
          ['〰️ CHOPPY', '#888888', 'Whipsaw. Best trade = no trade. 20% capital.'],
          ['📉 BEAR', '#ff6600', 'Deteriorating. No new longs. 10% capital.'],
          ['🛑 STRONG_BEAR', '#ff4444', 'Full distribution. 100% cash.'],
          ['⚡ EXTREME_OVERSOLD', '#ff8800', 'Capitulation. Wait for stabilization signal.'],
        ].map(([regime, color, desc], i) => (
          <View key={i} style={styles.regimeRow}>
            <Text style={[styles.regimeRowLabel, { color: color as string }]}>{regime as string}</Text>
            <Text style={styles.regimeRowDesc}>{desc as string}</Text>
          </View>
        ))}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>THE MENTAL EDGE</Text>
        <Text style={styles.bodyText}>
          Paul Annacone (Federer's coach): "Champions recognize when conditions aren't right for their game and adjust. Sitting out IS a decision."
          {'\n\n'}
          Jim Loehr: "The Ideal Performance State is calm, focused, and confident — not pumped up. Trade from that state."
          {'\n\n'}
          Djokovic: "Breathe. Reset. Next point." In trading: breathe, reset, next setup.
          {'\n\n'}
          Brad Gilbert: "Stop giving away free points." In chop, every forced trade is a free point given away.
        </Text>
      </View>
    </View>
  );
}

// ─── SHARED COMPONENTS ────────────────────────────────────────────────────────
function ScoreCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <View style={styles.scoreCard}>
      <Text style={styles.scoreLabel}>{label}</Text>
      <Text style={[styles.scoreValue, { color }]}>{value}</Text>
    </View>
  );
}

function MMRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <View style={styles.mmRow}>
      <Text style={styles.mmLabel}>{label}</Text>
      <Text style={[styles.mmValue, { color: color || T.text }]}>{value}</Text>
    </View>
  );
}

function BottomNav({ tab, setTab }: { tab: Tab; setTab: (t: Tab) => void }) {
  const tabs: { id: Tab; icon: string; label: string }[] = [
    { id: 'dashboard', icon: '📊', label: 'Today' },
    { id: 'briefing',  icon: '📋', label: 'Briefing' },
    { id: 'signals',   icon: '📡', label: 'Signals' },
    { id: 'history',   icon: '📈', label: 'History' },
    { id: 'learn',     icon: '🧠', label: 'Learn' },
  ];
  return (
    <View style={styles.nav}>
      {tabs.map(t => (
        <TouchableOpacity key={t.id} style={styles.navItem} onPress={() => setTab(t.id)}>
          <Text style={styles.navIcon}>{t.icon}</Text>
          <Text style={[styles.navLabel, { color: tab === t.id ? T.green : T.textDim }]}>{t.label}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

function LoadingScreen() {
  return (
    <View style={[styles.root, { justifyContent: 'center', alignItems: 'center' }]}>
      <ActivityIndicator size="large" color={T.green} />
      <Text style={[styles.bodyText, { marginTop: 16 }]}>Fetching MM data...</Text>
    </View>
  );
}

function EmptyState({ message }: { message?: string }) {
  return (
    <View style={{ padding: 30, alignItems: 'center' }}>
      <Text style={styles.bodyText}>{message || 'No briefing available yet. Pull down to refresh.'}</Text>
    </View>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <View style={styles.errorBanner}>
      <Text style={styles.errorText}>⚠️ {message}</Text>
    </View>
  );
}

function StaleBanner() {
  return (
    <View style={[styles.errorBanner, { backgroundColor: '#1a1a00' }]}>
      <Text style={[styles.errorText, { color: T.yellow }]}>
        ⏰ Briefing may be outdated. Pull down to refresh.
      </Text>
    </View>
  );
}

// ─── STYLES ───────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  root:           { flex: 1, backgroundColor: T.bg },
  content:        { flex: 1 },
  tab:            { padding: 16 },
  pageTitle:      { color: T.textBold, fontSize: 20, fontWeight: 'bold', marginBottom: 2 },
  dateText:       { color: T.textDim, fontSize: 12, marginBottom: 16 },
  card:           { backgroundColor: T.card, borderRadius: 12, padding: 16, marginBottom: 14, borderWidth: 1, borderColor: T.border },
  cardTitle:      { color: T.textDim, fontSize: 11, fontWeight: 'bold', letterSpacing: 1.2, textTransform: 'uppercase', marginBottom: 10 },
  bodyText:       { color: T.text, lineHeight: 22, fontSize: 14 },
  preText:        { color: T.text, lineHeight: 22, fontSize: 13, fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace' },
  bulletItem:     { color: T.text, fontSize: 13, lineHeight: 20, marginBottom: 4 },
  headline:       { color: T.textBold, fontSize: 15, lineHeight: 22, fontWeight: '600' },
  regimeBadge:    { borderRadius: 12, padding: 16, marginBottom: 14, alignItems: 'center' },
  regimeText:     { color: '#000', fontSize: 18, fontWeight: 'bold' },
  regimeDesc:     { color: '#000', fontSize: 12, marginTop: 4, opacity: 0.8 },
  scoreRow:       { flexDirection: 'row', gap: 10, marginBottom: 14 },
  scoreCard:      { flex: 1, backgroundColor: T.card, borderRadius: 10, padding: 12, alignItems: 'center', borderWidth: 1, borderColor: T.border },
  scoreLabel:     { color: T.textDim, fontSize: 10, textTransform: 'uppercase', letterSpacing: 1 },
  scoreValue:     { fontSize: 22, fontWeight: 'bold', marginTop: 4 },
  scanCard:       { backgroundColor: T.card, borderRadius: 12, padding: 16, marginBottom: 14, borderWidth: 2 },
  scanLabel:      { fontSize: 16, fontWeight: 'bold', marginBottom: 6 },
  scanAction:     { color: T.textBold, fontSize: 14, fontWeight: '600', marginBottom: 6 },
  scanDetail:     { color: T.text, fontSize: 13, lineHeight: 20 },
  turnaroundCard: { backgroundColor: '#1a1a0a', borderRadius: 12, padding: 16, marginBottom: 14, borderWidth: 1, borderColor: T.yellow },
  turnaroundTitle:{ color: T.yellow, fontSize: 14, fontWeight: 'bold', marginBottom: 8 },
  turnaroundText: { color: T.text, fontSize: 13, lineHeight: 20 },
  mmRow:          { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 5, borderBottomWidth: 1, borderBottomColor: T.border },
  mmLabel:        { color: T.textDim, fontSize: 13, flex: 1 },
  mmValue:        { color: T.text, fontSize: 13, fontWeight: '600', textAlign: 'right' },
  breakdownHeader:{ flexDirection: 'row', marginBottom: 6 },
  breakdownRow:   { flexDirection: 'row', paddingVertical: 5, borderBottomWidth: 1, borderBottomColor: T.border },
  breakdownCell:  { color: T.text, fontSize: 12 },
  chopBar:        { height: 10, backgroundColor: T.border, borderRadius: 5, marginBottom: 6, overflow: 'hidden' },
  chopFill:       { height: '100%', borderRadius: 5 },
  chopLabel:      { color: T.textDim, fontSize: 12, marginBottom: 8 },
  miniChart:      { flexDirection: 'row', alignItems: 'flex-end', height: 70, gap: 3, marginBottom: 8 },
  barWrapper:     { flex: 1, justifyContent: 'flex-end' },
  bar:            { borderRadius: 2, minHeight: 4 },
  chartLegend:    { flexDirection: 'row', gap: 12, flexWrap: 'wrap' },
  legendDot:      { fontSize: 11 },
  historyRow:     { backgroundColor: T.card, borderRadius: 10, padding: 12, marginBottom: 8, flexDirection: 'row', borderLeftWidth: 3 },
  historyLeft:    { flex: 1 },
  historyRight:   { flex: 2, flexDirection: 'row', flexWrap: 'wrap', gap: 6, justifyContent: 'flex-end' },
  historyDate:    { color: T.textBold, fontSize: 13, fontWeight: '600' },
  historyRegime:  { fontSize: 11, marginTop: 2 },
  historyVal:     { color: T.textDim, fontSize: 11 },
  anchorBox:      { borderLeftWidth: 3, borderLeftColor: T.green, paddingLeft: 12, marginBottom: 14 },
  anchorText:     { color: T.textBold, fontSize: 15, fontStyle: 'italic', lineHeight: 22 },
  webButton:      { backgroundColor: T.card, borderRadius: 10, padding: 14, alignItems: 'center', marginBottom: 14, borderWidth: 1, borderColor: T.border },
  webButtonText:  { color: T.green, fontSize: 14, fontWeight: '600' },
  learnRow:       { marginBottom: 12, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: T.border },
  learnName:      { color: T.textBold, fontSize: 13, fontWeight: '600', marginBottom: 3 },
  learnDesc:      { color: T.textDim, fontSize: 12, lineHeight: 18 },
  regimeRow:      { flexDirection: 'row', marginBottom: 8, alignItems: 'flex-start' },
  regimeRowLabel: { fontSize: 12, fontWeight: 'bold', width: 130 },
  regimeRowDesc:  { color: T.textDim, fontSize: 12, flex: 1, lineHeight: 18 },
  nav:            { flexDirection: 'row', backgroundColor: T.card2, borderTopWidth: 1, borderTopColor: T.border, paddingBottom: Platform.OS === 'ios' ? 20 : 0 },
  navItem:        { flex: 1, alignItems: 'center', paddingVertical: 10 },
  navIcon:        { fontSize: 20 },
  navLabel:       { fontSize: 10, marginTop: 2 },
  errorBanner:    { backgroundColor: '#1a0a0a', padding: 10, paddingHorizontal: 16 },
  errorText:      { color: T.red, fontSize: 12 },
});

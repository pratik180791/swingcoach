/**
 * SwingCoach Briefing Fetcher
 * Reads the daily briefing JSON from GitHub Pages.
 * No server needed — GitHub Pages is free and always on.
 *
 * SETUP: Replace YOUR_USERNAME with your GitHub username.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

// ─── CONFIG ───────────────────────────────────────────────────────────────────
// Replace YOUR_USERNAME with your actual GitHub username after forking the repo
const GITHUB_USERNAME = 'pratik180791';
const REPO_NAME = 'swingcoach';
const BASE_URL = `https://${GITHUB_USERNAME}.github.io/${REPO_NAME}`;

export const BRIEFING_URL = `${BASE_URL}/briefing.json`;
export const HISTORY_URL  = `${BASE_URL}/history.json`;
export const WEB_URL      = `${BASE_URL}/`;

const CACHE_KEY_BRIEFING = 'swingcoach_briefing_cache';
const CACHE_KEY_HISTORY  = 'swingcoach_history_cache';
const CACHE_TTL_MS = 4 * 60 * 60 * 1000; // 4 hours — refresh at most every 4h

// ─── TYPES ────────────────────────────────────────────────────────────────────
export interface BreakdownItem {
  component: string;
  label: string;
  score: number;
  value?: string;
}

export interface MMRaw {
  up4: number;
  dn4: number;
  ratio5: number;
  ratio10: number;
  up25qtr: number;
  dn25qtr: number;
  up25month: number;
  dn25month: number;
  up50month: number;
  dn50month: number;
  up13_34: number;
  dn13_34: number;
  t2108: number;
  bull_streak: number;
  bear_streak: number;
  breadth_thrust: boolean;
  net_breadth: number;
  net_breadth_5d: number;
  two_way_action: number;
  daily_ratio: number;
  qtr_ratio: number;
  ratio34_13: number;
  chop_score: number;
}

export interface Briefing {
  generated_at: string;
  date: string;
  regime: string;
  regime_color: string;
  regime_emoji: string;
  mm_score: number;
  chop_score: number;
  chop_regime: string;
  headline: string;
  trading_action: string;
  trading_action_detail: string;
  scan_tonight: boolean;
  scan_guidance: string;
  turnaround_signal: boolean;
  turnaround_detail: string;
  risk_pct: number;
  risk_level: string;
  key_signals: string[];
  breakdown: BreakdownItem[];
  action_items: string[];
  watch_for: string[];
  coach_note: string;
  mental_anchor: string;
  mental_reset: string;
  mm_raw: MMRaw;
}

export interface HistoryEntry {
  date: string;
  regime: string;
  mm_score: number;
  chop_score: number;
  scan_tonight: boolean;
  risk_pct: number;
  headline: string;
  up4: number;
  dn4: number;
  ratio5: number;
  up25qtr: number;
  dn25qtr: number;
  t2108: number;
  turnaround_signal: boolean;
}

// ─── FETCH WITH CACHE ─────────────────────────────────────────────────────────
async function fetchWithCache<T>(
  url: string,
  cacheKey: string,
  forceRefresh = false
): Promise<{ data: T; fromCache: boolean; error?: string }> {
  // Try cache first (unless forced refresh)
  if (!forceRefresh) {
    try {
      const cached = await AsyncStorage.getItem(cacheKey);
      if (cached) {
        const { data, timestamp } = JSON.parse(cached);
        const age = Date.now() - timestamp;
        if (age < CACHE_TTL_MS) {
          return { data, fromCache: true };
        }
      }
    } catch {}
  }

  // Fetch from network
  try {
    const response = await fetch(url, {
      headers: { 'Cache-Control': 'no-cache' },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: T = await response.json();

    // Save to cache
    await AsyncStorage.setItem(
      cacheKey,
      JSON.stringify({ data, timestamp: Date.now() })
    );

    return { data, fromCache: false };
  } catch (err: any) {
    // On network error, try returning stale cache
    try {
      const cached = await AsyncStorage.getItem(cacheKey);
      if (cached) {
        const { data } = JSON.parse(cached);
        return { data, fromCache: true, error: `Network error — showing cached data. ${err.message}` };
      }
    } catch {}

    return {
      data: null as any,
      fromCache: false,
      error: `Could not fetch data: ${err.message}. Check your internet connection.`,
    };
  }
}

// ─── PUBLIC API ───────────────────────────────────────────────────────────────
export async function fetchBriefing(
  forceRefresh = false
): Promise<{ briefing: Briefing | null; fromCache: boolean; error?: string }> {
  const result = await fetchWithCache<Briefing>(
    BRIEFING_URL,
    CACHE_KEY_BRIEFING,
    forceRefresh
  );
  return {
    briefing: result.data,
    fromCache: result.fromCache,
    error: result.error,
  };
}

export async function fetchHistory(
  forceRefresh = false
): Promise<{ history: HistoryEntry[]; fromCache: boolean; error?: string }> {
  const result = await fetchWithCache<HistoryEntry[]>(
    HISTORY_URL,
    CACHE_KEY_HISTORY,
    forceRefresh
  );
  return {
    history: result.data || [],
    fromCache: result.fromCache,
    error: result.error,
  };
}

// ─── HELPERS ──────────────────────────────────────────────────────────────────
export function getRegimeColor(regime: string): string {
  const colors: Record<string, string> = {
    BREADTH_THRUST: '#ff00ff',
    STRONG_BULL:    '#00ff88',
    BULL:           '#00cc66',
    NEUTRAL:        '#ffaa00',
    CHOPPY:         '#888888',
    BEAR:           '#ff6600',
    STRONG_BEAR:    '#ff4444',
    EXTREME_OVERSOLD: '#ff8800',
  };
  return colors[regime] || '#888888';
}

export function getRegimeDescription(regime: string): string {
  const desc: Record<string, string> = {
    BREADTH_THRUST:   'Launch pad. Maximum aggression.',
    STRONG_BULL:      'Broad participation. Load up on leaders.',
    BULL:             'Good conditions. Be selective.',
    NEUTRAL:          'Mixed signals. Reduce size.',
    CHOPPY:           'Whipsaw environment. Best trade = no trade.',
    BEAR:             'Breadth deteriorating. Protect capital.',
    STRONG_BEAR:      'Full distribution. 100% cash.',
    EXTREME_OVERSOLD: 'Capitulation zone. Wait for signal.',
  };
  return desc[regime] || '';
}

export function isDataStale(generatedAt: string): boolean {
  const generated = new Date(generatedAt);
  const now = new Date();
  const diffHours = (now.getTime() - generated.getTime()) / (1000 * 60 * 60);
  return diffHours > 28; // More than 28h old = likely missing a day
}

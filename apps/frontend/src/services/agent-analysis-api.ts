/**
 * Agent Analysis API: Analyst + Tutor agents for trade education
 */

import type { TContractInfo } from '@/components/summary/summary-card.types';

/** Mirrors LearningPayload from @ai-edu/shared */
export interface LearningPayload {
  contract: {
    contract_id: string;
    buy_price: number;
    payout: number;
    profit: number;
    currency: string;
    contract_type: string;
    shortcode: string;
    date_start: string;
    date_expiry: string;
    entry_tick?: string;
    exit_tick?: string;
  };
  strategy_intent?: unknown;
  behavioral_summary?: {
    run_id: string;
    trade_index_in_run: number;
    total_trades_in_run_so_far: number;
    recent_outcomes: ('win' | 'loss')[];
  };
}

// Use same origin when dev proxy is active (e.g. /api -> localhost:8000), else explicit URL
const AGENT_ANALYSIS_API =
  process.env.AGENT_ANALYSIS_API_URL || (typeof window !== 'undefined' ? '' : 'http://localhost:8000');

export interface AgentAnalysisResponse {
  version: number;
  trade_explanation: string;
  learning_recommendation: string;
  learning_points: string[];
  explanation_file?: string;
}

function toIsoDate(value: string | number | undefined): string {
  if (!value) return new Date().toISOString();
  if (typeof value === 'number') return new Date(value * 1000).toISOString();
  // Already formatted string - try to parse
  const d = new Date(value);
  return isNaN(d.getTime()) ? new Date().toISOString() : d.toISOString();
}

/**
 * Build LearningPayload from contract + optional run context
 */
export function buildLearningPayload(
  contract: TContractInfo,
  run_id?: string,
  trade_index?: number,
  recent_outcomes?: ('win' | 'loss')[]
): LearningPayload {
  const buy = contract.transaction_ids?.buy ?? contract.contract_id;
  return {
    contract: {
      contract_id: String(buy ?? contract.contract_id ?? 'unknown'),
      buy_price: Number(contract.buy_price) || 0,
      payout: Number(contract.payout) || Number(contract.bid_price) || 0,
      profit: Number(contract.profit) || 0,
      currency: contract.currency || 'USD',
      contract_type: contract.contract_type || 'CALL',
      shortcode: contract.shortcode || 'N/A',
      date_start: toIsoDate(contract.date_start ?? contract.purchase_time),
      date_expiry: toIsoDate((contract as any).date_expiry ?? contract.date_start),
      entry_tick: String(contract.entry_tick ?? contract.entry_spot ?? ''),
      exit_tick: String(contract.exit_tick ?? (contract as any).exit_spot ?? ''),
    },
    ...(run_id && trade_index !== undefined && recent_outcomes && {
      behavioral_summary: {
        run_id,
        trade_index_in_run: trade_index,
        total_trades_in_run_so_far: recent_outcomes.length,
        recent_outcomes,
      },
    }),
  };
}

export async function fetchAgentAnalysis(
  payload: LearningPayload,
  loginid?: string
): Promise<AgentAnalysisResponse> {
  const base = AGENT_ANALYSIS_API ? `${AGENT_ANALYSIS_API}` : '';
  const url = new URL(`${base}/api/agent_analysis/analyse/json`, window.location.origin);
  if (loginid) {
    url.searchParams.set('loginid', loginid);
  }
  const res = await fetch(url.toString(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.message || `API error ${res.status}`);
  }
  return res.json();
}

/**
 * Analyse trade with optional chart screenshot. Uses FormData; backend loads stored chart by contract_id when not provided.
 */
export async function fetchAgentAnalysisWithChart(
  payload: LearningPayload,
  options?: { chartBlob?: Blob | null; loginid?: string }
): Promise<AgentAnalysisResponse> {
  const base = AGENT_ANALYSIS_API ? `${AGENT_ANALYSIS_API}` : '';
  const url = new URL(`${base}/api/agent_analysis/analyse`, window.location.origin);
  if (options?.loginid) {
    url.searchParams.set('loginid', options.loginid);
  }
  const form = new FormData();
  form.append('payload_json', JSON.stringify(payload));
  if (options?.chartBlob) {
    form.append('chart_screenshot', options.chartBlob, 'chart.png');
  }
  const res = await fetch(url.toString(), {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.message || `API error ${res.status}`);
  }
  return res.json();
}

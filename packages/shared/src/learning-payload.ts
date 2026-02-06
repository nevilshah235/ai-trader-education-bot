/**
 * Learning payload: contract + strategy_intent + behavioral_summary
 * Sent from frontend to Intelligence Layer API
 */

import type { StrategyIntent } from './strategy-intent';

export interface LearningPayloadContract {
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
}

export interface BehavioralSummary {
  run_id: string;
  trade_index_in_run: number;
  total_trades_in_run_so_far: number;
  recent_outcomes: ('win' | 'loss')[];
}

export interface LearningPayload {
  contract: LearningPayloadContract;
  strategy_intent?: StrategyIntent;
  behavioral_summary?: BehavioralSummary;
}

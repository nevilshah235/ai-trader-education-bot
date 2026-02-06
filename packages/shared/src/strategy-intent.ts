/**
 * Strategy intent types aligned with strategy-intent.schema.json
 */

export interface StrategyIntentIntent {
  symbol?: string;
  trade_type?: string;
  contract_direction?: 'call' | 'put' | 'both';
  candle_interval?: string;
  restart_on_error?: boolean;
  time_machine?: boolean;
}

export interface StrategyIntentRisk {
  stake_or_payout?: 'stake' | 'payout';
  amount?: number;
  currency?: string;
  max_loss?: number | null;
  max_trades?: number | null;
  take_profit?: number | null;
  stop_loss?: number | null;
}

export interface StrategyIntentExit {
  has_custom_sell_conditions?: boolean;
  exit_on_expiry_only?: boolean;
  has_take_profit?: boolean;
  has_stop_loss?: boolean;
  trade_again_condition?: 'always' | 'conditional' | 'never';
}

export interface StrategyIntent {
  intent: StrategyIntentIntent;
  risk: StrategyIntentRisk;
  exit: StrategyIntentExit;
}

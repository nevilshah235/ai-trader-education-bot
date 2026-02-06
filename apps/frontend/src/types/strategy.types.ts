export type TStrategy = {
    id: string;
    name: string;
    save_type: string;
    timestamp: number;
    xml: string;
};

/** Minimal snapshot for learning/explanation: strategy intent, risk posture, exit philosophy. */
export type StrategyIntentSnapshot = {
    intent: {
        symbol?: string;
        trade_type?: string;
        contract_direction?: 'call' | 'put' | 'both';
        candle_interval?: string;
        restart_on_error?: boolean;
        time_machine?: boolean;
    };
    risk: {
        stake_or_payout?: 'stake' | 'payout';
        amount?: number;
        currency?: string;
        max_loss?: number;
        max_trades?: number;
        take_profit?: number;
        stop_loss?: number;
    };
    exit: {
        has_custom_sell_conditions?: boolean;
        exit_on_expiry_only?: boolean;
        has_take_profit?: boolean;
        has_stop_loss?: boolean;
        trade_again_condition?: 'always' | 'conditional' | 'never';
    };
};

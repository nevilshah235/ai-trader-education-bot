"""Pydantic models matching the trade JSON schema for Analyst/Tutor pipeline."""

from typing import Optional
from pydantic import BaseModel, Field


class Contract(BaseModel):
    contract_id: str
    buy_price: float
    payout: float
    profit: float
    currency: str
    contract_type: str
    shortcode: str
    date_start: str
    date_expiry: str
    entry_tick: Optional[str] = None
    exit_tick: Optional[str] = None


class StrategyIntentIntent(BaseModel):
    symbol: Optional[str] = None
    trade_type: Optional[str] = None
    contract_direction: Optional[str] = None
    candle_interval: Optional[str] = None
    restart_on_error: Optional[bool] = None
    time_machine: Optional[bool] = None


class StrategyIntentRisk(BaseModel):
    stake_or_payout: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    max_loss: Optional[float] = None
    max_trades: Optional[int] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None


class StrategyIntentExit(BaseModel):
    has_custom_sell_conditions: Optional[bool] = None
    exit_on_expiry_only: Optional[bool] = None
    has_take_profit: Optional[bool] = None
    has_stop_loss: Optional[bool] = None
    trade_again_condition: Optional[str] = None


class StrategyIntent(BaseModel):
    intent: StrategyIntentIntent = Field(default_factory=StrategyIntentIntent)
    risk: StrategyIntentRisk = Field(default_factory=StrategyIntentRisk)
    exit: StrategyIntentExit = Field(default_factory=StrategyIntentExit)


class BehavioralSummary(BaseModel):
    run_id: str
    trade_index_in_run: int
    total_trades_in_run_so_far: int
    recent_outcomes: list[str] = Field(default_factory=list)


class TradePayload(BaseModel):
    """Full payload: contract + strategy_intent + behavioral_summary."""
    contract: Contract
    strategy_intent: Optional[StrategyIntent] = None
    behavioral_summary: Optional[BehavioralSummary] = None


class AnalystOutput(BaseModel):
    """Structured output from Analyst Agent."""
    trade_analysis: str
    key_factors: list[str] = Field(default_factory=list)
    win_loss_assessment: str


class TutorOutput(BaseModel):
    """Structured output from Tutor Agent."""
    explanation: str
    learning_points: list[str] = Field(default_factory=list)

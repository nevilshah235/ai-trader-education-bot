"""SQLAlchemy models for Transaction and AnalysisResult. Align with TradePayload/Contract and agent outputs."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Transaction(Base):
    """Stored trade/contract: full Contract fields + optional strategy_intent and behavioral_summary."""

    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("user_id", "contract_id", name="uq_user_contract"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)  # loginid
    contract_id = Column(String(64), nullable=False, index=True)
    run_id = Column(String(128), nullable=True, index=True)

    # Contract fields
    buy_price = Column(Float, nullable=False)
    payout = Column(Float, nullable=False)
    profit = Column(Float, nullable=False)
    currency = Column(String(16), nullable=False)
    contract_type = Column(String(32), nullable=False)
    shortcode = Column(String(256), nullable=False)
    date_start = Column(String(64), nullable=False)
    date_expiry = Column(String(64), nullable=False)
    entry_tick = Column(String(64), nullable=True)
    exit_tick = Column(String(64), nullable=True)

    # Optional JSON: StrategyIntent and BehavioralSummary when provided
    strategy_intent = Column(JSON, nullable=True)
    behavioral_summary = Column(JSON, nullable=True)

    # Chart screenshot (base64 PNG) for analyst agent
    chart_image_b64 = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    analysis_results = relationship("AnalysisResult", back_populates="transaction", cascade="all, delete-orphan")


class AnalysisResult(Base):
    """Stored analyst + tutor outputs for a transaction."""

    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)

    # AnalystOutput
    trade_analysis = Column(Text, nullable=True)
    key_factors = Column(JSON, nullable=True)  # list[str]
    win_loss_assessment = Column(Text, nullable=True)

    # TutorOutput
    trade_explanation = Column(Text, nullable=True)
    learning_points = Column(JSON, nullable=True)  # list[str]
    explanation_file = Column(String(256), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="analysis_results")

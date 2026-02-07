"""CRUD for AnalysisResult. Link to Transaction by transaction_id."""

from sqlalchemy.orm import Session

from db.models import AnalysisResult, Transaction


def create_analysis_result(
    session: Session,
    *,
    transaction_id: int,
    trade_analysis: str | None = None,
    key_factors: list[str] | None = None,
    win_loss_assessment: str | None = None,
    trade_explanation: str | None = None,
    learning_points: list[str] | None = None,
    explanation_file: str | None = None,
) -> AnalysisResult:
    """Insert an analysis result linked to a transaction."""
    row = AnalysisResult(
        transaction_id=transaction_id,
        trade_analysis=trade_analysis,
        key_factors=key_factors or [],
        win_loss_assessment=win_loss_assessment,
        trade_explanation=trade_explanation,
        learning_points=learning_points or [],
        explanation_file=explanation_file,
    )
    session.add(row)
    return row


def get_latest_analysis_for_contract(
    session: Session,
    user_id: str,
    contract_id: str,
) -> AnalysisResult | None:
    """Get the most recent analysis for a user's contract."""
    tx = session.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.contract_id == contract_id,
    ).first()
    if not tx or not tx.analysis_results:
        return None
    return max(tx.analysis_results, key=lambda r: r.created_at)

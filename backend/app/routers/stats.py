from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Wallet
from app.schemas import StatsResponse

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _count_by_column(db: Session, column) -> dict:
    rows = db.query(column, func.count()).group_by(column).all()
    return {str(val or "Unknown"): count for val, count in rows}


def _review_short(status: str) -> str:
    mapping = {
        "AI Review": "A",
        "Manual Review": "M",
        "Reviewed": "R",
    }
    return mapping.get(status, status)


@router.get("", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Wallet.address)).scalar() or 0

    by_review_raw = _count_by_column(db, Wallet.review_status)
    by_review = {}
    for key, val in by_review_raw.items():
        short = _review_short(key)
        by_review[short] = by_review.get(short, 0) + val

    return StatsResponse(
        total_wallets=total,
        by_client_type=_count_by_column(db, Wallet.client_type),
        by_client_tier=_count_by_column(db, Wallet.client_tier),
        by_freq_cycle=_count_by_column(db, Wallet.freq_cycle),
        by_freq_tier=_count_by_column(db, Wallet.freq_tier),
        by_purity=_count_by_column(db, Wallet.purity),
        by_review=by_review,
        by_data_source=_count_by_column(db, Wallet.data_source),
    )

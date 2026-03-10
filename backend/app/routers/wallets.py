import io
import csv
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc

from app.database import get_db
from app.models import Wallet
from app.schemas import (
    WalletResponse,
    WalletListResponse,
    AnalyzeRequest,
    BulkAnalyzeRequest,
    ReviewRequest,
)
from app.services.classification import classification_engine

router = APIRouter(prefix="/api/wallets", tags=["wallets"])


@router.get("", response_model=WalletListResponse)
def list_wallets(
    client_type: Optional[str] = None,
    client_tier: Optional[str] = None,
    freq_cycle: Optional[str] = None,
    freq_tier: Optional[str] = None,
    purity: Optional[str] = None,
    review_status: Optional[str] = None,
    data_source: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    sort: str = Query("update_time"),
    order: str = Query("desc"),
    db: Session = Depends(get_db),
):
    query = db.query(Wallet)

    # Apply filters
    if client_type:
        query = query.filter(Wallet.client_type == client_type)
    if client_tier:
        query = query.filter(Wallet.client_tier == client_tier)
    if freq_cycle:
        query = query.filter(Wallet.freq_cycle == freq_cycle)
    if freq_tier:
        query = query.filter(Wallet.freq_tier == freq_tier)
    if purity:
        query = query.filter(Wallet.purity == purity)
    if review_status:
        query = query.filter(Wallet.review_status == review_status)
    if data_source:
        query = query.filter(Wallet.data_source == data_source)
    if search:
        query = query.filter(Wallet.address.ilike(f"%{search}%"))

    total = query.count()

    # Sorting
    sort_column = getattr(Wallet, sort, Wallet.update_time)
    if order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Pagination
    offset = (page - 1) * limit
    wallets = query.offset(offset).limit(limit).all()
    total_pages = (total + limit - 1) // limit

    return WalletListResponse(
        wallets=[WalletResponse.model_validate(w) for w in wallets],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/export")
def export_wallets(
    format: str = Query("csv"),
    client_type: Optional[str] = None,
    client_tier: Optional[str] = None,
    freq_cycle: Optional[str] = None,
    freq_tier: Optional[str] = None,
    purity: Optional[str] = None,
    review_status: Optional[str] = None,
    data_source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Wallet)

    if client_type:
        query = query.filter(Wallet.client_type == client_type)
    if client_tier:
        query = query.filter(Wallet.client_tier == client_tier)
    if freq_cycle:
        query = query.filter(Wallet.freq_cycle == freq_cycle)
    if freq_tier:
        query = query.filter(Wallet.freq_tier == freq_tier)
    if purity:
        query = query.filter(Wallet.purity == purity)
    if review_status:
        query = query.filter(Wallet.review_status == review_status)
    if data_source:
        query = query.filter(Wallet.data_source == data_source)

    wallets = query.all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Address", "Data Source", "Client Type", "Client Tier",
        "Review Status", "Freq Cycle", "Freq Tier", "Purity",
        "Funded By", "Total Amount", "TX in Period", "Token Count",
        "ETH Balance", "Wallet Created", "Collection Date",
        "Update Time", "Label", "Notes",
    ])

    for w in wallets:
        writer.writerow([
            w.address, w.data_source, w.client_type, w.client_tier,
            w.review_status, w.freq_cycle, w.freq_tier, w.purity,
            w.funded_by, w.total_amount, w.tx_in_period, w.token_count,
            w.eth_balance, w.wallet_created, w.collection_date,
            w.update_time, w.label, w.notes,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=wallets_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"},
    )


@router.get("/{address}", response_model=WalletResponse)
def get_wallet(address: str, db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.address == address.lower()).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return WalletResponse.model_validate(wallet)


@router.post("/analyze", response_model=WalletResponse)
async def analyze_wallet(req: AnalyzeRequest, db: Session = Depends(get_db)):
    result = await classification_engine.analyze_address(req.address, db)
    return result


@router.post("/bulk-analyze")
async def bulk_analyze(req: BulkAnalyzeRequest, db: Session = Depends(get_db)):
    results = []
    for address in req.addresses:
        try:
            result = await classification_engine.analyze_address(address, db)
            results.append(result)
        except Exception as e:
            results.append({"address": address, "error": str(e)})
    return results


@router.put("/{address}/review", response_model=WalletResponse)
def review_wallet(address: str, req: ReviewRequest, db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.address == address.lower()).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    if req.review_status:
        wallet.review_status = req.review_status
    if req.client_type:
        wallet.client_type = req.client_type
    if req.notes is not None:
        wallet.notes = req.notes

    wallet.update_time = datetime.utcnow()
    db.commit()
    db.refresh(wallet)
    return WalletResponse.model_validate(wallet)

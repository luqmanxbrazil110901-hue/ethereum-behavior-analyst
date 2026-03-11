from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class WalletBase(BaseModel):
    address: str


class WalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    address: str
    client_type: Optional[str] = None
    client_tier: Optional[str] = None
    freq_cycle: Optional[str] = None
    freq_tier: Optional[str] = None
    purity: Optional[str] = None
    review_status: Optional[str] = None
    data_source: Optional[str] = None
    eth_balance: Optional[float] = None
    total_amount: Optional[float] = None
    token_count: Optional[int] = None
    tx_in_period: Optional[int] = None
    is_contract: Optional[bool] = None
    funded_by: Optional[str] = None
    wallet_created: Optional[date] = None
    collection_date: Optional[date] = None
    update_time: Optional[datetime] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    label: Optional[str] = None
    notes: Optional[str] = None
    on_watchlist: Optional[bool] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    confidence: Optional[str] = None
    contamination_score: Optional[float] = None
    tx_30d: Optional[int] = None
    tx_90d: Optional[int] = None
    volume_30d_usd: Optional[float] = None
    volume_90d_usd: Optional[float] = None
    active_days_30d: Optional[int] = None
    reasons: Optional[List[str]] = None


class WalletListResponse(BaseModel):
    wallets: List[WalletResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class AnalyzeRequest(BaseModel):
    address: str


class BulkAnalyzeRequest(BaseModel):
    addresses: List[str]


class ReviewRequest(BaseModel):
    review_status: Optional[str] = None
    client_type: Optional[str] = None
    notes: Optional[str] = None


class StatsResponse(BaseModel):
    total_wallets: int
    by_client_type: Dict[str, int]
    by_client_tier: Dict[str, int]
    by_freq_cycle: Dict[str, int]
    by_freq_tier: Dict[str, int]
    by_purity: Dict[str, int]
    by_review: Dict[str, int]
    by_data_source: Dict[str, int]


class LabelCreate(BaseModel):
    address: str
    label: str
    category: str
    is_toxic: bool = False
    source: Optional[str] = None


class LabelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    address: str
    label: str
    category: str
    is_toxic: bool
    source: Optional[str] = None
    created_at: Optional[datetime] = None

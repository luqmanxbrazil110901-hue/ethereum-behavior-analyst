from sqlalchemy import Column, String, Integer, BigInteger, Numeric, Boolean, Date, DateTime, Text, SmallInteger, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class Wallet(Base):
    __tablename__ = "wallets"

    address = Column(String(42), primary_key=True)

    # Classification
    client_type = Column(String(10))
    client_tier = Column(String(5))
    freq_cycle = Column(String(5))
    freq_tier = Column(String(5))
    purity = Column(String(5))
    review_status = Column(String(20), default="Manual Review")

    # Data Source
    data_source = Column(String(5), default="R")

    # On-chain data
    eth_balance = Column(Numeric, default=0)
    total_amount = Column(Numeric, default=0)
    token_count = Column(Integer, default=0)
    tx_in_period = Column(Integer, default=0)
    is_contract = Column(Boolean, default=False)

    # Relationships
    funded_by = Column(String(42))

    # Timestamps
    wallet_created = Column(Date)
    collection_date = Column(Date, default=func.current_date())
    update_time = Column(DateTime, default=func.now())
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)

    # Metadata
    label = Column(String(100))
    notes = Column(Text)
    on_watchlist = Column(Boolean, default=False)

    created_at = Column(DateTime, default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    tx_hash = Column(String(66), primary_key=True)
    block_number = Column(BigInteger, nullable=False)
    block_timestamp = Column(DateTime, nullable=False)
    from_address = Column(String(42), nullable=False)
    to_address = Column(String(42))
    value_wei = Column(Numeric)
    gas_used = Column(BigInteger)
    gas_price = Column(Numeric)
    method_sig = Column(String(10))
    status = Column(SmallInteger)
    created_at = Column(DateTime, default=func.now())


class TokenTransfer(Base):
    __tablename__ = "token_transfers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tx_hash = Column(String(66), nullable=False)
    block_number = Column(BigInteger, nullable=False)
    block_timestamp = Column(DateTime, nullable=False)
    token_address = Column(String(42), nullable=False)
    from_address = Column(String(42), nullable=False)
    to_address = Column(String(42), nullable=False)
    value = Column(Numeric)
    token_type = Column(String(10))
    created_at = Column(DateTime, default=func.now())


class KnownLabel(Base):
    __tablename__ = "known_labels"

    address = Column(String(42), primary_key=True)
    label = Column(String(100), nullable=False)
    category = Column(String(20), nullable=False)
    is_toxic = Column(Boolean, default=False)
    source = Column(String(50))
    created_at = Column(DateTime, default=func.now())


class ClassificationLog(Base):
    __tablename__ = "classification_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    address = Column(String(42), nullable=False)
    client_type = Column(String(10))
    client_tier = Column(String(5))
    freq_cycle = Column(String(5))
    freq_tier = Column(String(5))
    purity = Column(String(5))
    signals = Column(JSONB)
    classified_at = Column(DateTime, default=func.now())

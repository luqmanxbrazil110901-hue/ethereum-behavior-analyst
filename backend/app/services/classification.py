import logging
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models import Wallet, Transaction, TokenTransfer, KnownLabel, ClassificationLog
from app.services.blockchain import blockchain_service

logger = logging.getLogger(__name__)

# ERC-20 Transfer event topic
ERC20_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


class ClassificationEngine:

    async def analyze_address(self, address: str, db: Session, data_source: str = "R") -> Dict[str, Any]:
        """Full analysis pipeline for a single address."""
        address = address.lower().strip()

        # Fetch on-chain data
        balance = await blockchain_service.get_balance(address)
        tx_count = await blockchain_service.get_transaction_count(address)
        is_contract = await blockchain_service.is_contract(address)
        eth_price = await blockchain_service.get_eth_price()

        # Check known labels
        known = db.query(KnownLabel).filter(KnownLabel.address == address).first()

        # Get transactions from DB for this address
        txs = db.query(Transaction).filter(
            or_(Transaction.from_address == address, Transaction.to_address == address)
        ).order_by(Transaction.block_timestamp.asc()).all()

        # Calculate metrics
        total_value_eth = sum(float(tx.value_wei or 0) / 1e18 for tx in txs)
        total_value_usd = total_value_eth * eth_price
        if balance is not None:
            total_value_usd += balance * eth_price

        tx_count_period = len(txs)

        # Token transfers
        token_transfers = db.query(TokenTransfer).filter(
            or_(TokenTransfer.from_address == address, TokenTransfer.to_address == address)
        ).all()
        unique_tokens = len(set(tt.token_address for tt in token_transfers))

        # Determine funded_by
        funded_by = None
        if txs:
            first_incoming = next(
                (tx for tx in txs if tx.to_address == address and float(tx.value_wei or 0) > 0),
                None
            )
            if first_incoming:
                funded_by = first_incoming.from_address

        # First/last seen
        first_seen = txs[0].block_timestamp if txs else None
        last_seen = txs[-1].block_timestamp if txs else None
        wallet_created = first_seen.date() if first_seen else None

        # Classification
        client_type = self._classify_type(address, txs, known, db)
        client_tier = self._classify_tier(total_value_usd)
        freq_cycle = self._classify_freq_cycle(txs)
        freq_tier = self._classify_freq_tier(tx_count_period)
        purity = self._classify_purity(address, funded_by, db)
        review_status = self._determine_review_status(client_type, known)

        signals = {
            "eth_balance": balance,
            "tx_count_nonce": tx_count,
            "tx_count_period": tx_count_period,
            "total_value_eth": total_value_eth,
            "total_value_usd": total_value_usd,
            "eth_price_used": eth_price,
            "unique_tokens": unique_tokens,
            "is_contract": is_contract,
            "has_known_label": known is not None,
        }

        # Upsert wallet
        wallet = db.query(Wallet).filter(Wallet.address == address).first()
        now = datetime.utcnow()

        wallet_data = {
            "address": address,
            "client_type": client_type,
            "client_tier": client_tier,
            "freq_cycle": freq_cycle,
            "freq_tier": freq_tier,
            "purity": purity,
            "review_status": review_status,
            "data_source": data_source,
            "eth_balance": balance or 0,
            "total_amount": total_value_usd,
            "token_count": unique_tokens,
            "tx_in_period": tx_count_period,
            "is_contract": is_contract,
            "funded_by": funded_by,
            "wallet_created": wallet_created,
            "collection_date": date.today(),
            "update_time": now,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "label": known.label if known else None,
            "on_watchlist": wallet.on_watchlist if wallet else False,
        }

        if wallet:
            for key, value in wallet_data.items():
                if key != "address":
                    setattr(wallet, key, value)
        else:
            wallet = Wallet(**wallet_data)
            db.add(wallet)

        # Log classification
        log_entry = ClassificationLog(
            address=address,
            client_type=client_type,
            client_tier=client_tier,
            freq_cycle=freq_cycle,
            freq_tier=freq_tier,
            purity=purity,
            signals=signals,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(wallet)

        return wallet_data

    def _classify_type(self, address: str, txs: list, known: Optional[KnownLabel], db: Session) -> str:
        # Check known labels first
        if known:
            category_map = {
                "exchange": "E",
                "bridge": "B",
                "mixer": "AP",
                "scam": "AP",
            }
            if known.is_toxic:
                return "AP"
            if known.category in category_map:
                return category_map[known.category]

        if not txs:
            return "U"

        # Bot detection: high frequency, regular intervals, few unique contracts
        if len(txs) >= 100:
            timestamps = [tx.block_timestamp for tx in txs if tx.block_timestamp]
            if len(timestamps) >= 2:
                intervals = [
                    (timestamps[i + 1] - timestamps[i]).total_seconds()
                    for i in range(len(timestamps) - 1)
                ]
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    std_dev = (sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)) ** 0.5
                    # Very regular timing suggests bot
                    if std_dev < avg_interval * 0.1 and avg_interval < 300:
                        return "S"

        # Check if funded by toxic address
        if txs:
            first_incoming = next(
                (tx for tx in txs if tx.to_address == address and float(tx.value_wei or 0) > 0),
                None,
            )
            if first_incoming:
                funder_label = db.query(KnownLabel).filter(
                    KnownLabel.address == first_incoming.from_address
                ).first()
                if funder_label and funder_label.is_toxic:
                    return "AP"

        return "U"

    def _classify_tier(self, total_value_usd: float) -> str:
        if total_value_usd >= 10_000_000:
            return "L5"
        elif total_value_usd >= 1_000_000:
            return "L4"
        elif total_value_usd >= 100_000:
            return "L3"
        elif total_value_usd >= 10_000:
            return "L2"
        else:
            return "L1"

    def _classify_freq_cycle(self, txs: list) -> str:
        if len(txs) < 2:
            return "Y"

        timestamps = sorted([tx.block_timestamp for tx in txs if tx.block_timestamp])
        if len(timestamps) < 2:
            return "Y"

        intervals = [
            (timestamps[i + 1] - timestamps[i]).total_seconds()
            for i in range(len(timestamps) - 1)
        ]
        avg_seconds = sum(intervals) / len(intervals)
        avg_days = avg_seconds / 86400

        if avg_days < 1:
            return "D"
        elif avg_days <= 7:
            return "W"
        elif avg_days <= 30:
            return "M"
        else:
            return "Y"

    def _classify_freq_tier(self, tx_count: int) -> str:
        if tx_count == 0:
            return "F1"
        elif tx_count <= 3:
            return "F2"
        elif tx_count <= 10:
            return "F3"
        elif tx_count <= 19:
            return "F4"
        else:
            return "F5"

    def _classify_purity(self, address: str, funded_by: Optional[str], db: Session) -> str:
        # Check if address itself is toxic
        own_label = db.query(KnownLabel).filter(
            KnownLabel.address == address,
            KnownLabel.is_toxic == True,
        ).first()
        if own_label:
            return "P"

        # Check if funded by toxic address
        if funded_by:
            funder_label = db.query(KnownLabel).filter(
                KnownLabel.address == funded_by,
                KnownLabel.is_toxic == True,
            ).first()
            if funder_label:
                return "P"

        # Check transactions with toxic addresses
        toxic_addresses = [
            row.address for row in db.query(KnownLabel.address).filter(KnownLabel.is_toxic == True).all()
        ]
        if toxic_addresses:
            toxic_tx = db.query(Transaction).filter(
                or_(
                    and_(Transaction.from_address == address, Transaction.to_address.in_(toxic_addresses)),
                    and_(Transaction.to_address == address, Transaction.from_address.in_(toxic_addresses)),
                )
            ).first()
            if toxic_tx:
                return "P"

        return "C"

    def _determine_review_status(self, client_type: str, known: Optional[KnownLabel]) -> str:
        if known:
            return "AI Review"
        if client_type != "U":
            return "AI Review"
        return "Manual Review"


classification_engine = ClassificationEngine()

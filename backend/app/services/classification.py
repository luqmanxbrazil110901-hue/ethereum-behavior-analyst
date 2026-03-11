import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import ClassificationLog, KnownLabel, TokenTransfer, Transaction, Wallet
from app.services.blockchain import blockchain_service

logger = logging.getLogger(__name__)


class ClassificationEngine:
    async def analyze_address(
        self,
        address: str,
        db: Session,
        data_source: str = "R",
    ) -> Dict[str, Any]:
        """Run the full classification pipeline for one address."""
        address = address.lower().strip()

        balance = await blockchain_service.get_balance(address)
        tx_count = await blockchain_service.get_transaction_count(address)
        is_contract = await blockchain_service.is_contract(address)
        eth_price = await blockchain_service.get_eth_price() or 0.0

        known = db.query(KnownLabel).filter(KnownLabel.address == address).first()
        txs = (
            db.query(Transaction)
            .filter(or_(Transaction.from_address == address, Transaction.to_address == address))
            .order_by(Transaction.block_timestamp.asc())
            .all()
        )

        total_value_eth = sum(float(tx.value_wei or 0) / 1e18 for tx in txs)
        total_value_usd = total_value_eth * eth_price
        if balance is not None:
            total_value_usd += float(balance) * eth_price

        tx_count_period = len(txs)
        token_transfers = (
            db.query(TokenTransfer)
            .filter(or_(TokenTransfer.from_address == address, TokenTransfer.to_address == address))
            .all()
        )
        unique_tokens = len({tt.token_address for tt in token_transfers if tt.token_address})

        funded_by = None
        if txs:
            first_incoming = next(
                (tx for tx in txs if tx.to_address == address and float(tx.value_wei or 0) > 0),
                None,
            )
            if first_incoming:
                funded_by = first_incoming.from_address

        first_seen = txs[0].block_timestamp if txs else None
        last_seen = txs[-1].block_timestamp if txs else None
        wallet_created = first_seen.date() if first_seen else None

        client_type = self._classify_type(address, txs, known, db)
        client_tier = self._classify_tier(total_value_usd)
        freq_cycle = self._classify_freq_cycle(txs)
        freq_tier = self._classify_freq_tier(tx_count_period)
        purity = self._classify_purity(address, funded_by, db)
        review_status = self._determine_review_status(client_type, known)

        window = self._compute_window_metrics(txs, eth_price)
        contamination_score = self._compute_contamination_score(address, funded_by, txs, db)
        risk_score, risk_level = self._compute_risk(
            client_type=client_type,
            purity=purity,
            contamination_score=contamination_score,
            tx_count_period=tx_count_period,
            is_contract=is_contract,
        )
        confidence = self._compute_confidence(known, tx_count_period)
        reasons = self._build_reasons(
            client_type=client_type,
            purity=purity,
            funded_by=funded_by,
            known=known,
            tx_count_period=tx_count_period,
            contamination_score=contamination_score,
        )

        signals = {
            "eth_balance": float(balance or 0),
            "tx_count_nonce": tx_count,
            "tx_count_period": tx_count_period,
            "total_value_eth": total_value_eth,
            "total_value_usd": total_value_usd,
            "eth_price_used": eth_price,
            "unique_tokens": unique_tokens,
            "is_contract": is_contract,
            "has_known_label": known is not None,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "confidence": confidence,
            "contamination_score": contamination_score,
            "reasons": reasons,
            **window,
        }

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
            "eth_balance": float(balance or 0),
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

        return {
            **wallet_data,
            "notes": wallet.notes,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "confidence": confidence,
            "contamination_score": contamination_score,
            **window,
        }

    def _compute_window_metrics(self, txs: List[Transaction], eth_price: float) -> Dict[str, float]:
        now = datetime.utcnow()
        d30 = now - timedelta(days=30)
        d90 = now - timedelta(days=90)

        txs_30 = [tx for tx in txs if tx.block_timestamp and tx.block_timestamp >= d30]
        txs_90 = [tx for tx in txs if tx.block_timestamp and tx.block_timestamp >= d90]

        vol_30_eth = sum(float(tx.value_wei or 0) / 1e18 for tx in txs_30)
        vol_90_eth = sum(float(tx.value_wei or 0) / 1e18 for tx in txs_90)
        active_days_30 = len({tx.block_timestamp.date() for tx in txs_30 if tx.block_timestamp})

        return {
            "tx_30d": len(txs_30),
            "tx_90d": len(txs_90),
            "volume_30d_usd": vol_30_eth * eth_price,
            "volume_90d_usd": vol_90_eth * eth_price,
            "active_days_30d": active_days_30,
        }

    def _compute_contamination_score(
        self,
        address: str,
        funded_by: Optional[str],
        txs: List[Transaction],
        db: Session,
    ) -> float:
        score = 0.0

        own_toxic = (
            db.query(KnownLabel)
            .filter(KnownLabel.address == address, KnownLabel.is_toxic.is_(True))
            .first()
        )
        if own_toxic:
            score += 0.7

        if funded_by:
            toxic_funder = (
                db.query(KnownLabel)
                .filter(KnownLabel.address == funded_by, KnownLabel.is_toxic.is_(True))
                .first()
            )
            if toxic_funder:
                score += 0.3

        toxic_addresses = {
            row.address
            for row in db.query(KnownLabel.address).filter(KnownLabel.is_toxic.is_(True)).all()
        }
        if txs and toxic_addresses:
            toxic_touch = 0
            for tx in txs:
                from_address = (tx.from_address or "").lower()
                to_address = (tx.to_address or "").lower()
                if (from_address == address and to_address in toxic_addresses) or (
                    to_address == address and from_address in toxic_addresses
                ):
                    toxic_touch += 1

            ratio = toxic_touch / max(len(txs), 1)
            score += min(0.4, ratio * 0.4)

        return min(1.0, score)

    def _compute_risk(
        self,
        client_type: str,
        purity: str,
        contamination_score: float,
        tx_count_period: int,
        is_contract: bool,
    ) -> tuple[float, str]:
        score = 5.0

        if purity == "P":
            score += 50
        score += contamination_score * 30

        if client_type == "AP":
            score += 30
        elif client_type == "S":
            score += 15

        if is_contract:
            score += 5

        if tx_count_period > 200:
            score += 10
        elif tx_count_period > 50:
            score += 5

        score = min(100.0, score)
        if score >= 70:
            return score, "high"
        if score >= 35:
            return score, "medium"
        return score, "low"

    def _compute_confidence(self, known: Optional[KnownLabel], tx_count_period: int) -> str:
        if known or tx_count_period >= 50:
            return "high"
        if tx_count_period >= 10:
            return "medium"
        return "low"

    def _build_reasons(
        self,
        client_type: str,
        purity: str,
        funded_by: Optional[str],
        known: Optional[KnownLabel],
        tx_count_period: int,
        contamination_score: float,
    ) -> List[str]:
        reasons: List[str] = []

        if known:
            reasons.append(f"Known label matched: {known.category or 'unknown'}")
            if known.is_toxic:
                reasons.append("Address is marked toxic")

        if funded_by:
            reasons.append(f"First incoming funder: {funded_by}")

        if client_type == "S":
            reasons.append("Pattern suggests automated behavior")
        if client_type == "AP":
            reasons.append("Potentially abusive pattern detected")
        if purity == "P":
            reasons.append("Toxic exposure detected")

        if tx_count_period == 0:
            reasons.append("No local transaction history yet")
        elif tx_count_period < 5:
            reasons.append("Limited transaction sample")

        if contamination_score >= 0.6:
            reasons.append("High contamination score")
        elif contamination_score >= 0.3:
            reasons.append("Moderate contamination score")

        return reasons

    def _classify_type(
        self,
        address: str,
        txs: List[Transaction],
        known: Optional[KnownLabel],
        db: Session,
    ) -> str:
        if known:
            category_map = {
                "exchange": "E",
                "bridge": "B",
                "mixer": "AP",
                "scam": "AP",
            }
            if known.is_toxic:
                return "AP"

            mapped_type = category_map.get((known.category or "").lower())
            if mapped_type:
                return mapped_type

        if not txs:
            return "U"

        if len(txs) >= 100:
            timestamps = [tx.block_timestamp for tx in txs if tx.block_timestamp]
            if len(timestamps) >= 2:
                intervals = [
                    (timestamps[index + 1] - timestamps[index]).total_seconds()
                    for index in range(len(timestamps) - 1)
                ]
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    std_dev = (
                        sum((interval - avg_interval) ** 2 for interval in intervals) / len(intervals)
                    ) ** 0.5
                    if avg_interval > 0 and std_dev < avg_interval * 0.1 and avg_interval < 300:
                        return "S"

        first_incoming = next(
            (tx for tx in txs if tx.to_address == address and float(tx.value_wei or 0) > 0),
            None,
        )
        if first_incoming:
            funder_label = (
                db.query(KnownLabel)
                .filter(KnownLabel.address == first_incoming.from_address)
                .first()
            )
            if funder_label and funder_label.is_toxic:
                return "AP"

        return "U"

    def _classify_tier(self, total_value_usd: float) -> str:
        if total_value_usd >= 10_000_000:
            return "L5"
        if total_value_usd >= 1_000_000:
            return "L4"
        if total_value_usd >= 100_000:
            return "L3"
        if total_value_usd >= 10_000:
            return "L2"
        return "L1"

    def _classify_freq_cycle(self, txs: List[Transaction]) -> str:
        if len(txs) < 2:
            return "Y"

        timestamps = sorted(tx.block_timestamp for tx in txs if tx.block_timestamp)
        if len(timestamps) < 2:
            return "Y"

        intervals = [
            (timestamps[index + 1] - timestamps[index]).total_seconds()
            for index in range(len(timestamps) - 1)
        ]
        avg_seconds = sum(intervals) / len(intervals)
        avg_days = avg_seconds / 86400

        if avg_days < 1:
            return "D"
        if avg_days <= 7:
            return "W"
        if avg_days <= 30:
            return "M"
        return "Y"

    def _classify_freq_tier(self, tx_count: int) -> str:
        if tx_count == 0:
            return "F1"
        if tx_count <= 3:
            return "F2"
        if tx_count <= 10:
            return "F3"
        if tx_count <= 19:
            return "F4"
        return "F5"

    def _classify_purity(self, address: str, funded_by: Optional[str], db: Session) -> str:
        own_label = (
            db.query(KnownLabel)
            .filter(KnownLabel.address == address, KnownLabel.is_toxic.is_(True))
            .first()
        )
        if own_label:
            return "P"

        if funded_by:
            funder_label = (
                db.query(KnownLabel)
                .filter(KnownLabel.address == funded_by, KnownLabel.is_toxic.is_(True))
                .first()
            )
            if funder_label:
                return "P"

        toxic_addresses = [
            row.address for row in db.query(KnownLabel.address).filter(KnownLabel.is_toxic.is_(True)).all()
        ]
        if toxic_addresses:
            toxic_tx = (
                db.query(Transaction)
                .filter(
                    or_(
                        and_(Transaction.from_address == address, Transaction.to_address.in_(toxic_addresses)),
                        and_(Transaction.to_address == address, Transaction.from_address.in_(toxic_addresses)),
                    )
                )
                .first()
            )
            if toxic_tx:
                return "P"

        return "C"

    def _determine_review_status(self, client_type: str, known: Optional[KnownLabel]) -> str:
        if known or client_type != "U":
            return "AI Review"
        return "Manual Review"


classification_engine = ClassificationEngine()

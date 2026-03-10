import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

import websockets
import httpx
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Wallet, Transaction, TokenTransfer
from app.services.classification import classification_engine
from app.config import settings

logger = logging.getLogger(__name__)

# ERC-20 Transfer event signature
ERC20_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


class BlockIndexer:
    def __init__(self):
        self.ws_url = settings.eth_rpc_ws
        self.rpc_url = settings.eth_rpc_http
        self.running = False

    async def _rpc_call(self, method: str, params: list = None):
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": 1,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.rpc_url, json=payload)
            result = resp.json()
            if "error" in result:
                logger.error(f"RPC error: {result['error']}")
                return None
            return result.get("result")

    async def start(self):
        """Subscribe to new block headers and process them."""
        self.running = True
        logger.info("Block indexer starting...")

        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    # Subscribe to new heads
                    sub_msg = {
                        "jsonrpc": "2.0",
                        "method": "eth_subscribe",
                        "params": ["newHeads"],
                        "id": 1,
                    }
                    await ws.send(json.dumps(sub_msg))
                    sub_response = await ws.recv()
                    logger.info(f"Subscribed to newHeads: {sub_response}")

                    while self.running:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=60)
                            data = json.loads(message)

                            if "params" in data and "result" in data["params"]:
                                block_header = data["params"]["result"]
                                block_number = int(block_header["number"], 16)
                                logger.info(f"New block: {block_number}")
                                await self._process_block(block_number)

                        except asyncio.TimeoutError:
                            # Send ping to keep connection alive
                            try:
                                await ws.ping()
                            except Exception:
                                break

            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if self.running:
                    logger.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)

    async def _process_block(self, block_number: int):
        """Process a block: check transactions against watchlisted addresses."""
        db = SessionLocal()
        try:
            # Get watchlisted addresses
            watchlisted = db.query(Wallet.address).filter(Wallet.on_watchlist == True).all()
            if not watchlisted:
                return

            watch_set = set(addr.address.lower().strip() for addr in watchlisted)

            # Fetch full block
            block = await self._rpc_call("eth_getBlockByNumber", [hex(block_number), True])
            if not block or not block.get("transactions"):
                return

            block_timestamp = datetime.utcfromtimestamp(int(block["timestamp"], 16))

            for tx in block["transactions"]:
                from_addr = (tx.get("from") or "").lower()
                to_addr = (tx.get("to") or "").lower()

                involved = set()
                if from_addr in watch_set:
                    involved.add(from_addr)
                if to_addr in watch_set:
                    involved.add(to_addr)

                if not involved:
                    continue

                # Store transaction
                tx_hash = tx["hash"]
                existing = db.query(Transaction).filter(Transaction.tx_hash == tx_hash).first()
                if not existing:
                    receipt = await self._rpc_call("eth_getTransactionReceipt", [tx_hash])
                    status = int(receipt["status"], 16) if receipt and "status" in receipt else None
                    gas_used = int(receipt["gasUsed"], 16) if receipt and "gasUsed" in receipt else None

                    new_tx = Transaction(
                        tx_hash=tx_hash,
                        block_number=int(tx["blockNumber"], 16),
                        block_timestamp=block_timestamp,
                        from_address=tx.get("from", ""),
                        to_address=tx.get("to", ""),
                        value_wei=int(tx.get("value", "0x0"), 16),
                        gas_used=gas_used,
                        gas_price=int(tx.get("gasPrice", "0x0"), 16),
                        method_sig=tx.get("input", "0x")[:10] if tx.get("input") else None,
                        status=status,
                    )
                    db.add(new_tx)

                    # Check for ERC-20 transfers in receipt logs
                    if receipt and receipt.get("logs"):
                        for log in receipt["logs"]:
                            if (
                                log.get("topics")
                                and len(log["topics"]) >= 3
                                and log["topics"][0] == ERC20_TRANSFER_TOPIC
                            ):
                                token_from = "0x" + log["topics"][1][-40:]
                                token_to = "0x" + log["topics"][2][-40:]
                                value = int(log.get("data", "0x0"), 16) if log.get("data") else 0

                                tt = TokenTransfer(
                                    tx_hash=tx_hash,
                                    block_number=int(tx["blockNumber"], 16),
                                    block_timestamp=block_timestamp,
                                    token_address=log["address"],
                                    from_address=token_from,
                                    to_address=token_to,
                                    value=value,
                                    token_type="ERC20",
                                )
                                db.add(tt)

                db.commit()

                # Re-classify involved wallets
                for addr in involved:
                    try:
                        await classification_engine.analyze_address(addr, db)
                    except Exception as e:
                        logger.error(f"Classification error for {addr}: {e}")

        except Exception as e:
            logger.error(f"Error processing block {block_number}: {e}")
            db.rollback()
        finally:
            db.close()

    def stop(self):
        self.running = False


block_indexer = BlockIndexer()

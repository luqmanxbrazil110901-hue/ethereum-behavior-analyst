import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class BlockchainService:
    def __init__(self) -> None:
        self.rpc_url = settings.eth_rpc_http
        self.beacon_url = settings.eth_beacon_api

    async def _rpc_call(self, method: str, params: Optional[list] = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": 1,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.rpc_url, json=payload)
            result = response.json()
            if "error" in result:
                logger.error("RPC error: %s", result["error"])
                return None
            return result.get("result")

    async def get_balance(self, address: str) -> Optional[float]:
        result = await self._rpc_call("eth_getBalance", [address, "latest"])
        if result is None:
            return None
        return int(result, 16) / 1e18

    async def get_transaction_count(self, address: str) -> Optional[int]:
        result = await self._rpc_call("eth_getTransactionCount", [address, "latest"])
        if result is None:
            return None
        return int(result, 16)

    async def is_contract(self, address: str) -> bool:
        result = await self._rpc_call("eth_getCode", [address, "latest"])
        if result is None:
            return False
        return result != "0x" and len(result) > 2

    async def get_block_number(self) -> Optional[int]:
        result = await self._rpc_call("eth_blockNumber")
        if result is None:
            return None
        return int(result, 16)

    async def get_block(self, block_number: int, full_tx: bool = True) -> Optional[Dict[str, Any]]:
        return await self._rpc_call("eth_getBlockByNumber", [hex(block_number), full_tx])

    async def get_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        return await self._rpc_call("eth_getTransactionByHash", [tx_hash])

    async def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        return await self._rpc_call("eth_getTransactionReceipt", [tx_hash])

    async def get_logs(
        self,
        from_block: int,
        to_block: int,
        address: Optional[str] = None,
        topics: Optional[list] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        params: Dict[str, Any] = {
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
        }
        if address:
            params["address"] = address
        if topics:
            params["topics"] = topics
        return await self._rpc_call("eth_getLogs", [params])

    async def get_eth_price(self) -> float:
        """Fetch ETH price from CoinGecko. Falls back to a default."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": "ethereum", "vs_currencies": "usd"},
                )
                data = response.json()
                return data["ethereum"]["usd"]
        except Exception as exc:
            logger.warning("Failed to fetch ETH price: %s, using default", exc)
            return 2500.0

    async def get_wallet_transactions_from_blocks(
        self,
        address: str,
        from_block: int,
        to_block: int,
    ) -> List[Dict[str, Any]]:
        """Scan blocks for transactions involving an address."""
        address_lower = address.lower()
        transactions: List[Dict[str, Any]] = []
        batch_size = 100

        for start in range(from_block, to_block + 1, batch_size):
            end = min(start + batch_size - 1, to_block)
            for block_num in range(start, end + 1):
                block = await self.get_block(block_num, full_tx=True)
                if not block or not block.get("transactions"):
                    continue

                block_timestamp = datetime.utcfromtimestamp(int(block["timestamp"], 16))
                for tx in block["transactions"]:
                    from_addr = (tx.get("from") or "").lower()
                    to_addr = (tx.get("to") or "").lower()
                    if from_addr == address_lower or to_addr == address_lower:
                        transactions.append(
                            {
                                "tx_hash": tx["hash"],
                                "block_number": int(tx["blockNumber"], 16),
                                "block_timestamp": block_timestamp,
                                "from_address": tx.get("from", ""),
                                "to_address": tx.get("to", ""),
                                "value_wei": int(tx.get("value", "0x0"), 16),
                                # Receipt data is unavailable here, so use tx gas as a fallback.
                                "gas_used": int(tx.get("gas", "0x0"), 16),
                                "gas_price": int(tx.get("gasPrice", "0x0"), 16),
                                "method_sig": tx.get("input", "0x")[:10] if tx.get("input") else None,
                            }
                        )

        return transactions


blockchain_service = BlockchainService()

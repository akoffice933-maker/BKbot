"""Read-only Polymarket service for market discovery and pricing."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import time
from collections import deque
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class PolymarketServiceError(RuntimeError):
    """Raised when Polymarket data cannot be retrieved or normalized."""


class PolymarketService:
    """Read-only client for Polymarket Gamma and CLOB APIs."""

    DEFAULT_GAMMA_HOST = "https://gamma-api.polymarket.com"

    def __init__(
        self,
        host: str,
        chain_id: int,
        *,
        gamma_host: str | None = None,
        client: httpx.AsyncClient | None = None,
        rate_limit_per_minute: int = 30,
    ) -> None:
        self.host = host.rstrip("/")
        self.chain_id = chain_id
        self.gamma_host = (gamma_host or self.DEFAULT_GAMMA_HOST).rstrip("/")
        self._client = client or self._build_client()
        self._owns_client = client is None
        self._rate_limit_per_minute = rate_limit_per_minute
        self._request_times: deque[float] = deque()
        self._rate_limit_lock = asyncio.Lock()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "PolymarketService":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    @staticmethod
    def _build_client() -> httpx.AsyncClient:
        http2_enabled = importlib.util.find_spec("h2") is not None
        return httpx.AsyncClient(http2=http2_enabled, timeout=10.0)

    async def search_markets(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search Polymarket markets using the public Gamma search endpoint."""
        payload = await self._request_json(
            self.gamma_host,
            "/public-search",
            params={
                "q": query,
                "limit_per_type": limit,
                "page": 1,
                "search_tags": "false",
                "search_profiles": "false",
                "optimized": "true",
            },
        )
        markets = self._extract_markets_from_search(payload)
        return markets[:limit]

    async def get_market(self, slug_or_id: str) -> dict[str, Any]:
        """Get a single market by slug or numeric ID."""
        try:
            if slug_or_id.isdigit():
                payload = await self._request_json(self.gamma_host, f"/markets/{slug_or_id}")
            else:
                payload = await self._request_json(self.gamma_host, f"/markets/slug/{slug_or_id}")
        except PolymarketServiceError:
            if slug_or_id.isdigit():
                raise
            fallback = await self._request_json(
                self.gamma_host,
                "/markets",
                params={"slug": slug_or_id},
            )
            if not isinstance(fallback, list) or not fallback:
                raise
            payload = fallback[0]

        return self._normalize_market(payload)

    async def get_price(self, token_id: str) -> dict[str, float]:
        """
        Return Polymarket share prices.

        A single token ID returns its price as "yes" and infers "no" as 1 - yes.
        Two token IDs separated by comma, pipe, or colon fetch both sides explicitly.
        """
        token_ids = self._split_token_ids(token_id)
        yes_price = await self._fetch_market_price(token_ids[0])

        if len(token_ids) > 1:
            no_price = await self._fetch_market_price(token_ids[1])
        else:
            no_price = round(max(0.0, min(1.0, 1.0 - yes_price)), 4)

        return {"yes": yes_price, "no": no_price}

    @staticmethod
    def price_to_odds(price: float) -> float:
        """Convert share price to decimal odds."""
        if not 0 < price < 1:
            raise ValueError("Price must be between 0 and 1")
        return round(1 / price, 4)

    @staticmethod
    def odds_to_price(odds: float) -> float:
        """Convert decimal odds to implied share price."""
        if odds <= 1:
            raise ValueError("Odds must be greater than 1")
        return round(1 / odds, 4)

    async def _fetch_market_price(self, token_id: str) -> float:
        payload = await self._request_json(
            self.host,
            "/price",
            params={"token_id": token_id, "side": "BUY"},
        )
        price = payload.get("price")
        if price is None:
            raise PolymarketServiceError(f"Price not found for token {token_id}")
        return float(price)

    async def _request_json(
        self,
        base_url: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        await self._throttle()
        url = f"{base_url}{path}"
        logger.info("Polymarket request: %s", url)

        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise PolymarketServiceError(f"Polymarket request failed: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise PolymarketServiceError("Polymarket returned invalid JSON") from exc

    async def _throttle(self) -> None:
        async with self._rate_limit_lock:
            now = time.monotonic()
            self._evict_old_requests(now)

            if len(self._request_times) >= self._rate_limit_per_minute:
                sleep_for = 60 - (now - self._request_times[0])
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                now = time.monotonic()
                self._evict_old_requests(now)

            self._request_times.append(now)

    def _evict_old_requests(self, now: float) -> None:
        while self._request_times and now - self._request_times[0] >= 60:
            self._request_times.popleft()

    def _extract_markets_from_search(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        raw_markets = []

        if isinstance(payload.get("markets"), list):
            raw_markets.extend(payload["markets"])

        for event in payload.get("events") or []:
            for market in event.get("markets") or []:
                raw_markets.append(market)

        normalized: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for market in raw_markets:
            normalized_market = self._normalize_market(market)
            market_id = normalized_market["id"]
            if market_id in seen_ids:
                continue
            seen_ids.add(market_id)
            normalized.append(normalized_market)

        return normalized

    def _normalize_market(self, market: dict[str, Any]) -> dict[str, Any]:
        outcomes = self._coerce_list(market.get("outcomes"))
        outcome_prices = self._coerce_list(market.get("outcomePrices"))
        token_ids = self._coerce_list(market.get("clobTokenIds"))

        yes_token = token_ids[0] if len(token_ids) > 0 else None
        no_token = token_ids[1] if len(token_ids) > 1 else None
        yes_price = self._coerce_float(outcome_prices[0]) if len(outcome_prices) > 0 else None
        no_price = self._coerce_float(outcome_prices[1]) if len(outcome_prices) > 1 else None

        return {
            "id": str(market.get("id")),
            "slug": market.get("slug"),
            "question": market.get("question"),
            "description": market.get("description"),
            "category": market.get("category"),
            "active": bool(market.get("active")),
            "closed": bool(market.get("closed")),
            "enable_order_book": bool(market.get("enableOrderBook")),
            "yes_token_id": yes_token,
            "no_token_id": no_token,
            "token_ids_csv": ",".join(token_ids) if token_ids else None,
            "yes_price": yes_price,
            "no_price": no_price,
            "outcomes": outcomes,
            "url": f"https://polymarket.com/event/{market.get('slug')}" if market.get("slug") else None,
            "raw": market,
        }

    @staticmethod
    def _split_token_ids(token_id: str) -> list[str]:
        for separator in (",", "|", ":"):
            if separator in token_id:
                return [part.strip() for part in token_id.split(separator) if part.strip()]
        return [token_id.strip()]

    @staticmethod
    def _coerce_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return [value]
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        return [str(value)]

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

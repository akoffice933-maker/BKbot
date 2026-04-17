import httpx
import pytest

from statbet_bot.services.polymarket import PolymarketService, PolymarketServiceError


def build_service(handler, *, rate_limit_per_minute: int = 30) -> PolymarketService:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return PolymarketService(
        "https://clob.polymarket.com",
        137,
        client=client,
        rate_limit_per_minute=rate_limit_per_minute,
    )


@pytest.mark.asyncio
async def test_search_markets_flattens_event_markets():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/public-search"
        assert request.url.params["q"] == "bitcoin"
        return httpx.Response(
            200,
            json={
                "events": [
                    {
                        "markets": [
                            {
                                "id": "1",
                                "slug": "btc-up",
                                "question": "Will BTC go up?",
                                "clobTokenIds": "[\"yes-token\",\"no-token\"]",
                                "outcomePrices": "[\"0.61\", \"0.39\"]",
                                "active": True,
                                "closed": False,
                            }
                        ]
                    }
                ]
            },
        )

    service = build_service(handler)
    try:
        markets = await service.search_markets("bitcoin")
    finally:
        await service.close()

    assert len(markets) == 1
    assert markets[0]["slug"] == "btc-up"
    assert markets[0]["yes_token_id"] == "yes-token"
    assert markets[0]["no_price"] == 0.39


@pytest.mark.asyncio
async def test_search_markets_deduplicates_markets():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "markets": [
                    {"id": "1", "slug": "dup", "question": "Q1"},
                    {"id": "1", "slug": "dup", "question": "Q1"},
                ]
            },
        )

    service = build_service(handler)
    try:
        markets = await service.search_markets("dup")
    finally:
        await service.close()

    assert len(markets) == 1


@pytest.mark.asyncio
async def test_get_market_by_slug_uses_slug_endpoint():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/markets/slug/fed-decision"
        return httpx.Response(
            200,
            json={
                "id": "42",
                "slug": "fed-decision",
                "question": "Will the Fed cut rates?",
                "clobTokenIds": "[\"token-yes\",\"token-no\"]",
                "outcomePrices": "[\"0.48\", \"0.52\"]",
                "active": True,
                "closed": False,
            },
        )

    service = build_service(handler)
    try:
        market = await service.get_market("fed-decision")
    finally:
        await service.close()

    assert market["id"] == "42"
    assert market["token_ids_csv"] == "token-yes,token-no"


@pytest.mark.asyncio
async def test_get_market_by_id_uses_id_endpoint():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/markets/123"
        return httpx.Response(200, json={"id": "123", "question": "Q"})

    service = build_service(handler)
    try:
        market = await service.get_market("123")
    finally:
        await service.close()

    assert market["id"] == "123"


@pytest.mark.asyncio
async def test_get_market_falls_back_to_query_slug_lookup_on_slug_404():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/markets/slug/custom-market":
            return httpx.Response(404, json={"error": "not found"})
        assert request.url.path == "/markets"
        return httpx.Response(200, json=[{"id": "5", "slug": "custom-market", "question": "Q"}])

    service = build_service(handler)
    try:
        market = await service.get_market("custom-market")
    finally:
        await service.close()

    assert calls == ["/markets/slug/custom-market", "/markets"]
    assert market["slug"] == "custom-market"


@pytest.mark.asyncio
async def test_get_price_single_token_infers_no_price():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/price"
        assert request.url.params["token_id"] == "token-yes"
        return httpx.Response(200, json={"price": 0.73})

    service = build_service(handler)
    try:
        price = await service.get_price("token-yes")
    finally:
        await service.close()

    assert price == {"yes": 0.73, "no": 0.27}


@pytest.mark.asyncio
async def test_get_price_pair_fetches_yes_and_no_tokens():
    async def handler(request: httpx.Request) -> httpx.Response:
        token_id = request.url.params["token_id"]
        if token_id == "token-yes":
            return httpx.Response(200, json={"price": 0.41})
        if token_id == "token-no":
            return httpx.Response(200, json={"price": 0.6})
        return httpx.Response(404, json={"error": "unknown token"})

    service = build_service(handler)
    try:
        price = await service.get_price("token-yes,token-no")
    finally:
        await service.close()

    assert price == {"yes": 0.41, "no": 0.6}


def test_price_to_odds_conversion():
    assert PolymarketService.price_to_odds(0.4) == 2.5


def test_odds_to_price_conversion():
    assert PolymarketService.odds_to_price(2.5) == 0.4


@pytest.mark.parametrize("price", [0, 1, -0.1, 1.1])
def test_price_to_odds_rejects_invalid_values(price):
    with pytest.raises(ValueError):
        PolymarketService.price_to_odds(price)


@pytest.mark.parametrize("odds", [1, 0, -3])
def test_odds_to_price_rejects_invalid_values(odds):
    with pytest.raises(ValueError):
        PolymarketService.odds_to_price(odds)


@pytest.mark.asyncio
async def test_service_wraps_http_errors():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    service = build_service(handler)
    try:
        with pytest.raises(PolymarketServiceError):
            await service.search_markets("btc")
    finally:
        await service.close()

import json
import requests
from bot.config import GAMMA_API_URL, GAMMA_API_PARAMS, MIN_VOLUME, MIN_VOLUME_24HR


def fetch_markets() -> list[dict]:
    """
    Fetch active markets from the Gamma API and return filtered list.
    Each item: {market_id, market_name, price, volume, slug}
    Sync — call via asyncio.to_thread() from async context.
    """
    try:
        response = requests.get(GAMMA_API_URL, params=GAMMA_API_PARAMS, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            print(f"[WARNING] Unexpected API response format: {type(data)}")
            return []

        markets = []
        for market in data:
            if not market.get("active") or market.get("closed") or not market.get("acceptingOrders"):
                continue

            volume_num = market.get("volumeNum", 0)
            volume_24hr = market.get("volume24hr", 0)
            if volume_num < MIN_VOLUME or volume_24hr < MIN_VOLUME_24HR:
                continue

            try:
                outcome_prices = market.get("outcomePrices", [])
                if isinstance(outcome_prices, str):
                    outcome_prices = json.loads(outcome_prices)
                price = float(outcome_prices[0]) if outcome_prices else 0.5

                markets.append({
                    "market_id": market.get("id"),
                    "market_name": market.get("question"),
                    "price": price,
                    "volume": volume_num,
                    "slug": market.get("slug"),
                })
            except (ValueError, IndexError, TypeError) as e:
                print(f"[WARNING] Failed to parse market {market.get('id')}: {e}")

        return markets

    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch markets: {e}")
        return []
    except Exception as e:
        print(f"[ERROR] Unexpected error in fetch_markets: {e}")
        return []
